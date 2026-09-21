# CropCred Phase 9 Hardening

## Production configuration

The frontend reads `VITE_API_BASE_URL` for the Flask API base URL. `VITE_API_URL` remains supported for compatibility. When neither is set, the frontend uses the relative `/api` path; it does not silently substitute seeded records after an API failure. The workspace displays an explicit live-API status banner and actionable error message when the API is unavailable.

For an Android build, set the API URL to a reachable HTTPS deployment before running the build:

```bash
export VITE_API_BASE_URL=https://api.example.com/api
export VITE_SOLANA_RPC_URL=https://api.devnet.solana.com
pnpm mobile:apk
```

The application must never use localhost, `127.0.0.1`, or `10.0.2.2` as a production API dependency.

## Flask startup

Install backend dependencies and initialize the database:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 -c "from database import init_db, seed_db; init_db(); seed_db()"
```

Run the production WSGI server:

```bash
gunicorn --bind 0.0.0.0:${PORT:-5000} app:app
```

Optional environment variables:

```bash
export CROP_CRED_CORS_ORIGINS=https://cropcred.example.com,https://app.example.com
export SOLANA_DEVNET_RPC_URL=https://api.devnet.solana.com
```

The backend rejects any configured RPC URL that does not identify Solana Devnet. CORS is restricted to the configured origins; `*` remains the development default.

## Android build

The sandbox Android SDK is located at `/home/ubuntu/android-sdk`:

```bash
cd /home/ubuntu/cropcred
printf 'sdk.dir=/home/ubuntu/android-sdk\n' > android/local.properties
ANDROID_HOME=/home/ubuntu/android-sdk ANDROID_SDK_ROOT=/home/ubuntu/android-sdk pnpm mobile:apk
```

APK output:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## Integrity and scope

Real payment verification remains backend-authoritative. Guided Demo Mode is explanatory only and does not create signatures, mark orders paid, or create Explorer proofs. Seeded records are presentation/demo data and are not external traction. CropCred uses Solana Devnet only and never requests or stores seed phrases or private keys.

Physical Android installation, wallet approval, and real Devnet settlement require an Android device and compatible wallet session; those steps cannot be simulated by the sandbox build.
