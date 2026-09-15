# CropCred Phase 6 — B2B Demand Network + Two-Sided Economic Trust

Phase 6 upgrades the existing B2B workspace into a structured demand network without replacing the marketplace, wallet, payment, delivery, or Economic Passport flows.

## Workflow

A buyer posts a demand request with product, quantity, unit, required date, frequency, price range, region, and requirements. A farmer can respond only while the demand is `OPEN`. Responses are stored with quantity, expected price, available date, and explicit lifecycle status. Buyers can inspect evidence-based farmer context and transparent match reasons before accepting one response. Acceptance creates a normal `PENDING_PAYMENT` CropCred order and delivery record, so the existing Solana Devnet payment and backend verification flow remains the single payment implementation.

## Data and APIs

The SQLite migration adds `buyer_profiles`, `demand_responses`, and lifecycle fields on existing `demands`. APIs include demand listing and creation, response submission, response review, response acceptance, buyer profile summaries, and farmer opportunity discovery. Buyer and farmer metrics are derived from existing orders, payments, deliveries, harvests, and Economic Passport records. Demonstration buyer profiles are labeled in the UI as network activity rather than real-world traction.

## Matching and privacy

Match fit is an explainable application metric based on quantity, date, price compatibility, relevant verified harvest, and verified payment history where available. It is not a trust score and does not use AI to decide farmer or buyer trustworthiness. Public passport privacy boundaries remain unchanged; response views show only commerce-relevant evidence and do not expose private buyer details or sensitive personal information.

## State transitions

Demand states are `OPEN`, `RESPONSES_RECEIVED`, `MATCHED`, `ORDER_CREATED`, `FULFILLED`, and `CANCELLED`. Response states are `SUBMITTED`, `SHORTLISTED`, `ACCEPTED`, `REJECTED`, and `WITHDRAWN`. The Phase 6 MVP supports one accepted farmer per demand; split fulfillment is intentionally deferred.
