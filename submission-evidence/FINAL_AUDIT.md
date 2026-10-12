# CropCred final audit evidence

Date: 2026-10-12
Repository: https://github.com/Vijayalakshmi2608/cropcred

## Scope

The audit preserves the React/TypeScript frontend, Flask/SQLite backend, Capacitor Android shell, Solana Devnet-only behavior, native Android Mobile Wallet Adapter bridge, and browser Groth16 proof flow.

## Implemented hardening

- Added backend payment-security regression coverage for wrong network, wrong payer, wrong recipient, wrong amount, failed/unconfirmed transactions, and transaction-signature replay.
- Added an idempotent SQLite partial unique index on non-null payment transaction signatures. This protects the one-signature/one-payment invariant during concurrent verification races.
- Added a reproducible Groth16 test command covering valid eligibility, valid ineligibility, tampering, malformed witness input, and stale passport fingerprint detection.
- Preserved the native Android MWA bridge. Its Phantom app identity icon uses the required relative URI (`/icon.svg`).
- Production API configuration remains `https://cropcred-api.onrender.com/api`; no localhost or temporary sandbox URL is used in production configuration.

## Validation commands and results

| Command | Result |
|---|---|
| `CROP_CRED_DB_PATH=/tmp/cropcred-final-audit.db PYTHONPATH=backend python3 -m unittest discover -s backend -p 'test_*.py' -v` | Passed: 8 tests |
| `pnpm test:zk` | Passed: valid, ineligible, tampered, malformed, stale-fingerprint cases |
| `pnpm check` | Passed |
| `pnpm build` | Passed; Vite analytics placeholders and chunk-size warnings only |
| `pnpm exec cap sync android` | Passed |
| `android/gradlew assembleDebug` | Passed |
| `apksigner verify` | Passed with APK Signature Scheme v2 |
| `git diff --check` | Passed |

## Remote service checks

- API health: `https://cropcred-api.onrender.com/api/health`
- API reported database ready, seeded data, and non-zero farmers, harvests, crop batches, listings, demands, and orders.
- Web CORS for `https://cropcred.onrender.com`: passed.
- Capacitor Android-origin CORS for `https://localhost`: passed.

## Honest boundaries

- No physical OPPO F9 or attached Android device was available in this environment. Install, Phantom approval/return, and live Devnet payment remain device-side checklist items.
- No real Devnet transaction was submitted by this audit. Payment tests use deterministic RPC-shaped fixtures for negative and invariant testing; they do not claim blockchain settlement.
- Render Free local SQLite storage is ephemeral across service replacement/restart. Use a persistent disk or managed database before treating the service as durable production infrastructure.
- The debug APK is suitable for direct development-device installation, not Play Store release.
