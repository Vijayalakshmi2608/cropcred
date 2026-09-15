# CropCred Phase 5 — Economic Passport Intelligence

Phase 5 turns the Economic Passport into a database-derived, evidence-first credential.

## What is included

- Versioned `economic_credentials` records with status, deterministic SHA-256 fingerprint, evidence count, and update timestamp.
- `credential_evidence` schema and evidence-aware activity APIs.
- Backend credential generation from verified harvests, paid orders, confirmed deliveries, and verified Solana payment records.
- Evidence and activity routes under `/api/farmers/:id/passport/*`.
- Public credential lookup under `/api/credentials/:credentialId` and selective sharing under `/api/credentials/:credentialId/share`.
- Dedicated Economic Passport intelligence page with activity summary, evidence-derived reliability metrics, explainability text, proof timeline, fingerprint, network/anchor state, and selective sharing controls.
- Public verification route `/verify/:credentialId` that exposes only credential-level evidence and explicitly distinguishes transaction verification from physical crop claims.

## Evidence principles

The passport does not use a subjective farmer score. Counts and percentages are calculated from SQLite records and verified payment/delivery relationships. If a metric lacks sufficient evidence, the UI displays `Insufficient verified activity`. Seeded historical orders without corresponding verified payment records do not count as blockchain payment proofs.

Credential fingerprints are canonical SHA-256 hashes of the public aggregate metric payload. A fingerprint is not a Solana transaction signature. Credential anchors remain `Awaiting credential anchor` until a real anchor mechanism exists; no fake transaction signature is generated.

## Privacy

The public route does not expose phone numbers, email, home address, government identifiers, private documents, seed phrases, private keys, or exact private buyer information. Selective sharing controls determine which evidence categories are included in the generated verification link.

## Verification language

CropCred uses precise distinctions: registered application evidence, verified evidence, blockchain transaction evidence verified on Solana Devnet, and commerce completion. Solana verifies the recorded transaction evidence; it does not independently prove crop quality, physical existence, or agricultural claims.
