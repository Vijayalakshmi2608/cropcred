import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, init_db, seed_db


class AuctionFlowTests(unittest.TestCase):
    def setUp(self):
        init_db()
        seed_db()
        self.client = app.test_client()

    def test_auction_round_trip_and_order_reuse(self):
        create_response = self.client.post('/api/auctions', json={
            'buyer_name': 'Green Valley Foods',
            'buyer_type': 'RESTAURANT',
            'crop': 'Tomatoes',
            'quantity': 250,
            'unit': 'kg',
            'price_min': 30,
            'price_max': 42,
            'deadline': '2026-10-05',
            'delivery_location': 'Coimbatore',
            'quality_requirements': 'Maturity grade A',
            'evidence_requirements': 'Photo + lot traceability',
            'crop_batch_id': 'CRP-1042'
        })
        self.assertEqual(create_response.status_code, 201, create_response.get_data(as_text=True))
        auction = create_response.get_json()['data']
        self.assertEqual(auction['status'], 'OPEN')

        offer_response = self.client.post(f"/api/auctions/{auction['id']}/offers", json={
            'farmer_id': 'farmer-01',
            'crop_batch_id': 'CRP-1042',
            'quantity': 220,
            'offered_price': 38,
            'delivery_estimate': '3 days',
            'message': 'Fresh harvest ready for delivery'
        })
        self.assertEqual(offer_response.status_code, 201, offer_response.get_data(as_text=True))
        offer = offer_response.get_json()['data']
        self.assertEqual(offer['status'], 'SUBMITTED')

        award_response = self.client.post(f"/api/auctions/{auction['id']}/award", json={'offer_id': offer['id']})
        self.assertEqual(award_response.status_code, 200, award_response.get_data(as_text=True))
        payload = award_response.get_json()['data']
        self.assertEqual(payload['auction']['status'], 'AWARDED')
        self.assertIn('order', payload)
        self.assertEqual(payload['order']['payment_status'], 'PENDING')

        list_response = self.client.get('/api/auctions')
        self.assertEqual(list_response.status_code, 200)
        self.assertGreater(len(list_response.get_json()['data']), 0)


class MarketIntelligenceTests(unittest.TestCase):
    def setUp(self):
        init_db()
        seed_db()
        self.client = app.test_client()

    def test_market_intelligence_api_returns_live_cropcred_data(self):
        response = self.client.get('/api/market-intelligence')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()['data']
        self.assertIn('overview', payload)
        self.assertIn('crop_demand', payload)
        self.assertIn('price_observations', payload)
        self.assertIn('insights', payload)
        self.assertGreater(payload['overview']['active_crop_batches'], 0)
        self.assertGreater(payload['price_observations']['transaction_count'], 0)

    def test_market_intelligence_insufficient_data_falls_back_cleanly(self):
        from database import get_connection
        connection = get_connection()
        connection.execute('DELETE FROM credential_evidence')
        connection.execute('DELETE FROM credential_verification_events')
        connection.execute('DELETE FROM economic_credentials')
        connection.execute('DELETE FROM payments')
        connection.execute('DELETE FROM deliveries')
        connection.execute('DELETE FROM demand_responses')
        connection.execute('DELETE FROM auction_offers')
        connection.execute('DELETE FROM crop_auctions')
        connection.execute('DELETE FROM orders')
        connection.execute('DELETE FROM marketplace_listings')
        connection.execute('DELETE FROM demands')
        connection.execute('DELETE FROM crop_batches')
        connection.execute('DELETE FROM harvests')
        connection.execute('DELETE FROM farmers')
        connection.execute('DELETE FROM market_insights')
        connection.commit()
        connection.close()

        response = self.client.get('/api/market-intelligence')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()['data']
        self.assertIn('Insufficient CropCred data for a reliable insight.', payload['insights'][0]['text'])
        self.assertGreaterEqual(payload['overview']['active_crop_batches'], 0)


if __name__ == '__main__':
    unittest.main()
