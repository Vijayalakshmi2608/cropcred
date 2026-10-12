# CropCred architecture and data flow

```text
React + TypeScript + Vite
        |
        | HTTPS /api
        v
Flask + Gunicorn + SQLite
        |
        +--> harvests -> crop_batches -> marketplace_listings -> orders -> deliveries
        |                                      |
        |                                      +--> payments / credential evidence
        |
        +--> Passport and economic credential aggregates

Android Capacitor shell
        +--> native Solana Mobile Wallet Adapter -> Phantom -> Solana Devnet

Browser ZK layer
        +--> Circom circuit + WASM witness + Groth16 zkey + verification key
```

## Source of truth

Stored agricultural, marketplace, order, demand, auction, delivery, payment, credential, and evidence records live in the backend SQLite schema. New harvests create linked batch/listing/evidence records. Inventory is reserved with conditional SQL updates and rejected when unavailable.

## Payment trust boundary

The wallet signs a Devnet transaction. The backend independently fetches and checks the confirmed transaction, fee payer, payer, recipient, exact lamports, transaction error, Devnet context, and one-time signature use. A frontend success flag alone cannot mark an order paid.

## Proof trust boundary

The Groth16 circuit proves the encoded threshold statement for the supplied witness. The browser verifies the proof using the packaged verification key and compares a SHA-256 fingerprint of the current Passport snapshot to reject stale local proof state. It does not independently prove physical crop quality or the truth of off-chain records.
