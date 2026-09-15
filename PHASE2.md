# CropCred Phase 2 — Flask + SQLite

The existing React/Tailwind frontend remains the primary UI. Phase 2 adds a lightweight Flask REST API and SQLite database under `backend/`.

## Start the backend on Windows

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The first start automatically creates `backend/cropcred.db`, creates all tables, and seeds realistic demo data.

## Start the frontend

```powershell
cd ..
pnpm install
$env:VITE_API_URL="http://localhost:5000/api"
pnpm dev
```

If `VITE_API_URL` is not set, the frontend attempts `http://localhost:5000/api` and falls back to the preserved Phase 1 local demo data when the backend is unavailable.

## API endpoints

| Area | Endpoints |
|---|---|
| Health | `GET /api/health` |
| Farmers | `GET /api/farmers`, `GET /api/farmers/:id`, `POST /api/farmers`, `PUT /api/farmers/:id` |
| Harvests | `GET /api/harvests`, `GET /api/harvests/:id`, `POST /api/harvests`, `PUT /api/harvests/:id` |
| Marketplace | `GET /api/marketplace`, `GET /api/marketplace/:id` |
| Demand | `GET /api/demands`, `GET /api/demands/:id` |
| Orders | `GET /api/orders`, `GET /api/orders/:id`, `POST /api/orders`, `PUT /api/orders/:id/status` |
| Delivery | `POST /api/deliveries/:order_id/confirm` |
| Passport | `GET /api/farmers/:id/passport` |

## Phase 2 boundaries

The backend intentionally does not implement authentication, wallet connection, Solana, payment processing, transaction signatures, blockchain anchoring, AI, KYC, loan approval, or credit scoring. New harvests are stored as `REGISTERED` with no proof hash. New orders are stored as `PLACED` / `PENDING` with a null transaction signature. Passport metrics are activity summaries, not a credit score.
