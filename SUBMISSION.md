# CropCred — Solana Mobile CLOCK IN Submission

CropCred is a mobile-first agricultural commerce and verification platform that turns structured farmer activity into a portable Economic Passport. It combines harvest registration, Verified Crop Batches, marketplace supply, B2B demand and auctions, orders, evidence, credentials, and real Solana Devnet settlement.

## Stack

- React, TypeScript, Vite, Tailwind CSS, Wouter, Lucide Icons
- Flask and SQLite REST API with additive idempotent migrations
- Capacitor Android shell
- Solana Web3.js and Solana Mobile Wallet Adapter
- Solana **Devnet only**

## Demonstrable farmer journey

1. Register a harvest. The record is explicitly registered, not blockchain verified.
2. Create a Verified Crop Batch linked to the harvest, with a deterministic fingerprint.
3. Publish or respond to marketplace/B2B demand.
4. Open a Crop Auction, compare farmer offers, and manually award one when applicable.
5. Awarding creates the existing `PENDING_PAYMENT` order and does not bypass payment.
6. Connect a compatible wallet on Devnet and explicitly approve the small test-SOL settlement.
7. The backend independently verifies confirmation, payer, recipient, amount, network, and signature replay state.
8. The Economic Passport keeps database evidence separate from blockchain transaction evidence.
9. A verified signature is available through the Solana Explorer Devnet link.

## Run and build

```bash
cd /home/ubuntu/cropcred
pnpm install
pnpm exec tsc --noEmit
pnpm build
```

Run the API:

```bash
cd backend
pip install -r requirements.txt
export SOLANA_DEVNET_RPC_URL=https://api.devnet.solana.com
export CROP_CRED_CORS_ORIGINS=http://localhost:3000
python3 app.py
```

For deployment or Android, configure a reachable HTTPS API:

```bash
export VITE_API_BASE_URL=https://your-api-host.example/api
export VITE_SOLANA_RPC_URL=https://api.devnet.solana.com
```

Do not use localhost, `127.0.0.1`, or `10.0.2.2` as the Android production API URL.

Build the debug APK:

```bash
printf 'sdk.dir=/home/ubuntu/android-sdk\n' > android/local.properties
ANDROID_HOME=/home/ubuntu/android-sdk ANDROID_SDK_ROOT=/home/ubuntu/android-sdk pnpm mobile:apk
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`.

## Honesty and security boundaries

- No seed phrases or private keys are requested or stored.
- Guided Demo Mode is explanatory only: it never opens a wallet, creates a signature, marks an order paid, or creates an Explorer proof.
- INR commerce value is separate from Devnet SOL settlement value.
- Database records and Solana transactions do not independently prove physical crop existence, quality, or quantity.
- No mainnet, token, staking, lending, DAO, DeFi, or speculative token economy is included.

## QA and limitations

TypeScript, production web build, backend compilation, idempotent database initialization, demand-to-auction API flow, auction offer/award-to-pending-order handoff, Passport evidence creation, Devnet-only source audit, and Android Gradle build were validated.

A physical Android device and compatible wallet app were not available in the sandbox, so final install, wallet approval, and live Devnet settlement remain device-side verification steps. The delivered APK is debug-signed rather than a Play Store release bundle. Production API hosting and CORS must be supplied before distribution outside the configured demonstration environment.
