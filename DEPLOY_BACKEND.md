# CropCred backend deployment runbook

## Current task capability

This task currently exposes only the Manus Sandbox. The persistent-environment check returned no Cloud Computer, VM, or attached WebDev project. The Sandbox is not suitable for the public API because its URL can expire when the session ends.

If you already own a Cloud Computer, attach it through the **computer icon below the chat input**. If you need to provision one, use [Create a Cloud Computer](https://manus.im/app#settings/my-computer/create), then select it from the computer picker and attach it to this task. The current repository is already prepared for a persistent Ubuntu host.

## Recommended third-party path: Railway Volume

Railway is the simplest external option for preserving the existing Flask + SQLite design:

- Railway documents Flask deployment with Gunicorn and public domain generation [1].
- Railway Volumes provide persistent read/write storage and expose the mount path at runtime [2].
- The application has been changed to read `CROP_CRED_DB_PATH`, so the database can live on the mounted volume.

A Render deployment also works, but a persistent disk must be attached to a paid web service; Render's free web services do not preserve local filesystem changes [3].

### Railway setup

1. Open Railway and create a new project from the GitHub repository `Vijayalakshmi2608/cropcred`.
2. Configure the service:
   - **Build command:** `pip install -r backend/requirements.txt`
   - **Start command:** `cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 1 --access-logfile - wsgi:app`
   - **Health check path:** `/api/health`
3. Create and attach a Volume to the API service. Use mount path:
   - `/data/cropcred`
4. Set these service variables:
   ```text
   CROP_CRED_DB_PATH=/data/cropcred/cropcred.db
   CROP_CRED_CORS_ORIGINS=https://cropcred-das-enwzdzle.manus.space,https://localhost,capacitor://localhost,http://localhost
   SOLANA_DEVNET_RPC_URL=https://api.devnet.solana.com
   ```
5. Generate a public Railway domain under the service's **Networking** settings. Use the resulting HTTPS URL as `<API_URL>` below, without a trailing slash.
6. Redeploy. The `backend/wsgi.py` entrypoint initializes the schema and idempotently seeds the farmer, harvest, crop-batch, marketplace, B2B-demand, auction, order, and credential data before Gunicorn accepts requests.

## Remote verification

Run these checks against the generated domain before rebuilding Android:

```bash
export API_URL=https://<your-railway-domain>

curl -fsS "$API_URL/api/health"
curl -fsS "$API_URL/api/harvests"
curl -fsS "$API_URL/api/crop-batches"
curl -fsS "$API_URL/api/marketplace"
curl -fsS "$API_URL/api/demands"
curl -fsS "$API_URL/api/auctions"
curl -fsS "$API_URL/api/orders"
curl -fsS "$API_URL/api/farmers/farmer-01/passport"

curl -i -X OPTIONS "$API_URL/api/harvests" \
  -H 'Origin: https://localhost' \
  -H 'Access-Control-Request-Method: GET'
```

The health response must contain `"status":"ok"`, `"database":"ready"`, `"seeded":true`, and non-zero counts for farmers, harvests, crop batches, marketplace listings, demands, and orders. The CORS response must include `Access-Control-Allow-Origin: https://localhost`.

Do not proceed to Android until all commands return HTTP 2xx and the CORS preflight is correct.

## Android production configuration

After the remote checks pass, replace the dead sandbox URL in `.env.production`:

```text
VITE_API_BASE_URL=https://<your-railway-domain>/api
VITE_SOLANA_RPC_URL=https://api.devnet.solana.com
VITE_APP_URL=https://cropcred-das-enwzdzle.manus.space
```

`capacitor.config.ts` already uses `androidScheme: 'https'` and `cleartext: false`. The API CORS list includes `https://localhost`, which is the Capacitor Android origin for this configuration, plus the legacy Capacitor origin forms.

Build and verify:

```bash
pnpm check
pnpm build
pnpm mobile:apk
```

The APK should be at:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

Verify the APK does not contain the old sandbox hostname:

```bash
unzip -p android/app/build/outputs/apk/debug/app-debug.apk \
  | strings | rg 'manus.computer|<your-railway-domain>'
```

Verify signing and checksum:

```bash
sha256sum android/app/build/outputs/apk/debug/app-debug.apk
$ANDROID_HOME/build-tools/<version>/apksigner verify --verbose \
  android/app/build/outputs/apk/debug/app-debug.apk
```

The final APK can then be uploaded to the existing GitHub release or a new release tag. The release URL must be tested with `curl -I -L` before being shared.

## Security constraints

- Keep `SOLANA_DEVNET_RPC_URL` on the Devnet host only.
- Do not weaken `cleartext: false` or add an HTTP API URL.
- Do not accept a payment as successful from a client-only flag; the existing backend verifies the Devnet transaction signature and transfer details.
- Keep the Groth16 circuit artifacts and browser verification unchanged.
- Run one Gunicorn worker for SQLite unless the database is migrated to a server database; concurrent multi-worker writes would require a different persistence design.

## References

[1]: https://docs.railway.com/guides/flask "Railway Flask deployment guide"
[2]: https://docs.railway.com/volumes "Railway Volumes documentation"
[3]: https://render.com/docs/free "Render free service limitations"
