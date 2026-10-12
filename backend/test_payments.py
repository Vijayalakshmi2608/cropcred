import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, init_db, seed_db
from database import get_connection

PAYER = "11111111111111111111111111111111"
RECIPIENT = "22222222222222222222222222222222"
SIGNATURE = "payment-test-signature-0001"


class PaymentVerificationTests(unittest.TestCase):
    def setUp(self):
        init_db()
        seed_db()
        self.client = app.test_client()
        connection = get_connection()
        connection.execute("UPDATE farmers SET wallet_address=? WHERE id='farmer-01'", (RECIPIENT,))
        connection.execute("DELETE FROM payments")
        connection.execute("UPDATE orders SET status='PLACED', payment_status='PENDING', transaction_signature=NULL WHERE id='CR-ORD-00219'")
        connection.commit()
        connection.close()

    def start_payment(self, order_id="CR-ORD-00219", payer=PAYER, network="devnet"):
        response = self.client.post(f"/api/orders/{order_id}/payment-intent", json={"payer_wallet": payer})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["data"]["network"], "devnet")
        if network != "devnet":
            self.fail("The API intentionally accepts only the Devnet payment-intent contract")

    @staticmethod
    def rpc_fixture(source=PAYER, destination=RECIPIENT, lamports=1_000_000, confirmation="confirmed", error=None):
        transaction = {
            "meta": {"err": error},
            "blockTime": 123456789,
            "transaction": {
                "message": {
                    "accountKeys": [{"pubkey": source}],
                    "instructions": [{"parsed": {"type": "transfer", "info": {
                        "source": source,
                        "destination": destination,
                        "lamports": lamports,
                    }}}],
                }
            },
        }
        statuses = {"value": [{"err": error, "confirmationStatus": confirmation}]}
        return lambda method, params: transaction if method == "getTransaction" else statuses

    def verify(self, signature=SIGNATURE, payer=PAYER, network="devnet", rpc=None):
        with patch("app.rpc_call", side_effect=rpc or self.rpc_fixture()):
            return self.client.post("/api/orders/CR-ORD-00219/verify-payment", json={
                "transaction_signature": signature,
                "payer_wallet": payer,
                "network": network,
            })

    def test_valid_devnet_transfer_verifies_once(self):
        self.start_payment()
        response = self.verify()
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["data"]["state"], "VERIFIED")
        connection = get_connection()
        row = connection.execute("SELECT payment_status, transaction_signature FROM orders WHERE id='CR-ORD-00219'").fetchone()
        connection.close()
        self.assertEqual(dict(row), {"payment_status": "PAID", "transaction_signature": SIGNATURE})

    def test_wrong_network_and_wrong_payer_are_rejected_without_rpc(self):
        self.start_payment()
        response = self.verify(network="mainnet-beta")
        self.assertEqual(response.status_code, 400)
        response = self.verify(payer="33333333333333333333333333333333")
        self.assertEqual(response.status_code, 400)

    def test_wrong_recipient_amount_failed_or_unconfirmed_transaction_is_not_paid(self):
        cases = [
            self.rpc_fixture(destination="33333333333333333333333333333333"),
            self.rpc_fixture(lamports=2_000_000),
            self.rpc_fixture(confirmation="processed"),
            self.rpc_fixture(error={"InstructionError": [0, "Custom"]}),
        ]
        for rpc in cases:
            with self.subTest(rpc=rpc):
                self.start_payment()
                response = self.verify(rpc=rpc)
                self.assertEqual(response.status_code, 400)
                connection = get_connection()
                row = connection.execute("SELECT payment_status, status FROM orders WHERE id='CR-ORD-00219'").fetchone()
                payment = connection.execute("SELECT status FROM payments WHERE order_id='CR-ORD-00219'").fetchone()
                connection.close()
                self.assertEqual(row["payment_status"], "PENDING")
                self.assertEqual(row["status"], "PAYMENT_FAILED")
                self.assertEqual(payment["status"], "FAILED")

    def test_verified_signature_cannot_be_reused_for_another_order(self):
        self.start_payment()
        self.assertEqual(self.verify().status_code, 200)
        connection = get_connection()
        listing = connection.execute("SELECT id, farmer_id FROM marketplace_listings WHERE quantity_available > 1 LIMIT 1").fetchone()
        connection.execute("UPDATE farmers SET wallet_address=? WHERE id=?", (RECIPIENT, listing["farmer_id"]))
        connection.commit()
        connection.close()
        created = self.client.post("/api/orders", json={"listing_id": listing["id"], "quantity": 1, "buyer_name": "Replay Test Buyer"})
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        second_order = created.get_json()["data"]["id"]
        self.assertEqual(self.client.post(f"/api/orders/{second_order}/payment-intent", json={"payer_wallet": PAYER}).status_code, 200)
        response = self.client.post(f"/api/orders/{second_order}/verify-payment", json={"transaction_signature": SIGNATURE, "payer_wallet": PAYER, "network": "devnet"})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
