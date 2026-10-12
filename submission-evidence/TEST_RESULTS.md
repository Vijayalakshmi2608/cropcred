# CropCred automated test results

Run date: 2026-10-12

## Passed commands

| Command | Actual result |
|---|---|
| `CROP_CRED_DB_PATH=/tmp/cropcred-final-audit.db PYTHONPATH=backend python3 -m unittest discover -s backend -p 'test_*.py' -v` | 8 tests passed |
| `pnpm test:zk` | Passed: valid, ineligible, tampered, malformed, stale-fingerprint cases |
| `pnpm check` | TypeScript passed |
| `pnpm build` | Vite and server bundle passed |
| `pnpm exec cap sync android` | Capacitor sync passed |
| `cd android && ./gradlew assembleDebug` | Android build passed |
| `apksigner verify --verbose android/app/build/outputs/apk/debug/app-debug.apk` | v2 signature verified; 1 signer |
| `git diff --check` | Passed |

## Backend test breakdown

The eight passing tests are the existing auction and market-intelligence coverage, production WSGI startup coverage, and four payment-security tests. The payment tests use deterministic RPC-shaped fixtures and verify that client-only claims cannot settle an order. They do not claim that a real Devnet transaction was submitted.

## Final APK

The current public release asset is:

https://github.com/Vijayalakshmi2608/cropcred/releases/download/v1.0.0-clock-in/CropCred-final-audited-debug.apk

Size: `5,457,606` bytes

SHA-256: `48b2223f8e1cb5404c301b55c017ef0b2e08f94e1bd386735b5c9fc9da8f6ab6`

The public asset was downloaded and matched the locally built APK checksum after the Phantom relative-icon fix.

## Physical-device status

The sandbox has no attached OPPO F9 or compatible Phantom session. Physical installation, wallet approval/return, and live Devnet settlement remain pending and are listed in `DEVICE_CHECKLIST.md`.
