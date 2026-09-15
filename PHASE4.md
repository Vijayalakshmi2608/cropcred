# CropCred Phase 4 — Verified Solana Devnet Payments

Phase 4 adds a real, non-custodial native SOL settlement flow for marketplace orders.

## Flow

1. A marketplace order starts as `PENDING_PAYMENT`.
2. The buyer opens the order and selects **Pay with Solana Devnet**.
3. The backend creates a payment intent after validating the order, buyer wallet, and farmer settlement wallet.
4. The browser constructs a native SOL transfer using `@solana/web3.js` and the farmer's stored public address.
5. The connected wallet opens for explicit approval. CropCred never receives private keys or seed phrases.
6. The real Devnet signature is confirmed through Solana Devnet RPC.
7. The signature is sent to Flask, which independently verifies the confirmed transaction, buyer, recipient, network, and minimum lamport amount.
8. Only after backend verification does the payment become `VERIFIED`, the order become `PAID`, and the farmer credential counters update.

## Demo settlement amount

Marketplace values remain denominated in INR. Phase 4 uses a clearly labeled fixed demo settlement of **0.001 SOL** on Devnet. Devnet SOL has no real monetary value and is used for testing.

## Error and safety behavior

The flow blocks without a connected Devnet wallet or seller settlement wallet, resets an unpaid payment after wallet rejection, prevents duplicate verified payment intents, shows faucet guidance through the existing wallet panel, and never creates fake signatures, explorer URLs, or paid states. Transaction proof is external blockchain evidence; it does not independently prove crop quality or physical existence.

## Testing

Start the Flask API from `backend/` and the frontend with `pnpm dev`. Connect Phantom on Solana Devnet, fund the buyer wallet from the official Devnet faucet, open an unpaid order, and choose **Pay with Solana Devnet**. Approve the transaction, then confirm the real signature opens the Devnet Solana Explorer and that the order and Economic Passport reflect verified payment evidence.

The sandbox validation covers production build, backend compilation, schema migration, health, invalid-wallet rejection, payment-intent creation, cancellation, credential lookup, and route rendering. A real payment requires a user-controlled Devnet wallet and cannot be fabricated in automated tests.
