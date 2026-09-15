# CropCred Phase 7 — Insights, Validation, and Founder Intelligence

Phase 7 adds an evidence-first founder intelligence layer to the existing CropCred marketplace, Economic Passport, Solana Devnet payment flow, and B2B demand network.

## What is included

The `/insights` workspace is a responsive founder console organized around product activity, recorded validation, product learnings, pilot opportunities, GTM experiments, founder decisions, and credential verification events. It includes a product funnel from farmers and registered harvests through orders, verified payments, deliveries, credentials, and public verification events. Commerce and B2B panels calculate observed marketplace activity from the SQLite database, while validation and pilot panels remain empty until the founder enters real evidence.

The interface explicitly classifies data as **Product Activity**, **Validation**, or **External Traction**. Product activity is derived from CropCred's own records. Validation is manually entered through founder-controlled forms. External traction is not fabricated; the default state is “No external traction recorded yet.” The product makes no claims about market size, adoption, revenue, financing outcomes, or customer success beyond the records present in the application database.

## Backend additions

SQLite now includes `validation_interviews`, `product_learnings`, `pilot_participants`, `founder_notes`, `gtm_experiments`, and `credential_verification_events`. The migration is additive and runs through the existing `init_db()` path.

New endpoints include:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/insights/overview` | Consolidated founder dashboard snapshot |
| `GET /api/insights/product-funnel` | Product activity funnel values |
| `GET /api/insights/commerce` | Observed marketplace activity |
| `GET /api/insights/b2b` | Observed demand and response activity |
| `GET /api/insights/credentials` | Credential issuance and verification metrics |
| `GET/POST /api/validation/interviews` | Founder-entered validation conversations |
| `GET/POST /api/product-learnings` | Discovery-to-change learning records |
| `GET/POST /api/pilots` | Pilot opportunity pipeline |
| `GET/POST /api/gtm-experiments` | Founder-controlled GTM experiment log |
| `GET/POST /api/founder-notes` | Evidence-linked product decisions |
| `GET/POST /api/credential-verification-events` | Credential verification event log |

## Honest uncertainty boundaries

CropCred Insights is not an automated investor or lender. It does not create a trust score, infer customer validation, invent pilot participants, fabricate traction, or imply that a credential guarantees financing. The unresolved founder question remains visible in the UI: **will buyers value reusable economic credentials enough to change their verification workflow?**

All blockchain language is separated into locally-derived credential evidence, Solana Devnet payment verification, and optional on-chain anchoring. A credential is not described as immutable or financially predictive unless a corresponding record exists.

## Verification

- `python3 -m py_compile backend/app.py backend/database.py`
- Additive SQLite migration and initialization completed successfully.
- Phase 7 overview, funnel, commerce, B2B, credential, and validation APIs smoke-tested.
- Temporary validation smoke record removed after testing.
- `pnpm build` completed successfully.
- Desktop and mobile `/insights` screenshots reviewed.
- Honesty scan completed for fabricated traction, prohibited trust-score claims, and financing guarantees.
