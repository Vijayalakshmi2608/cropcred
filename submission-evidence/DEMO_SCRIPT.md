# CropCred judge demo script

1. Open the deployed CropCred frontend and show the farmer dashboard.
2. Open **Harvests** and register or edit a harvest. Explain that the Flask API stores the harvest, linked crop batch, evidence record, and marketplace listing in one SQLite source of truth.
3. Open **Crop Batches** and show the harvest-to-batch fingerprint and evidence timeline.
4. Open **Marketplace**, choose a listing, and create a preorder. Explain that inventory is reserved atomically and overselling is rejected.
5. Open **B2B Demand** to show demand → farmer response → accepted match → order creation.
6. Open **Orders** and show the order in pending payment. Do not claim paid status without a real Devnet transaction.
7. On an attached Android device, connect Phantom on Solana Devnet, approve the real small SOL transfer, and show backend verification plus the Explorer link. If no device is available, state that this step is pending rather than simulating it.
8. Open **Economic Passport** and show stored harvest, sale, payment, delivery, credential, and activity evidence.
9. Open **Private Economic Proof**. Generate a Groth16 proof, explain that sales remain a private witness while the threshold and eligibility result are public, then run local verification.
10. End with the security boundary: Devnet only, no seed phrases/private keys, no fabricated signatures, and no physical validation claimed unless performed.
