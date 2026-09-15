# CropCred Phase 3 — Solana Devnet Wallet Identity

Phase 3 adds a lightweight, non-custodial wallet identity layer while preserving the Phase 1/2 experience.

## What is included

- Shared `SolanaWalletProvider` and `useSolanaWallet()` hook.
- Phantom-compatible browser provider support through `window.solana`.
- Devnet-only network labeling and balance reads through `@solana/web3.js`.
- Copyable shortened wallet addresses, connect/disconnect states, friendly errors, Devnet faucet link, and wallet identity panels.
- Public wallet address persistence through `PUT /api/farmers/:id/wallet`.
- Server-side validation for plausible Solana base58 public keys.
- Wallet association stored in the existing `farmers.wallet_address` column; disconnect clears it to `NULL`.

## Connect a Devnet wallet

1. Install Phantom or another compatible Solana browser wallet.
2. Switch the wallet network to **Solana Devnet**.
3. Open CropCred and select **Connect Solana Wallet**.
4. Approve the public-address connection in the wallet popup.
5. Confirm the shortened address and `Solana Devnet` indicator in the top bar and Profile page.

The app never asks for seed phrases, private keys, wallet passwords, or secret keys. Phase 3 does not sign transactions and does not initiate payments.

## Phase 3 limitations

Wallet connection is identity association only. It is not agricultural verification, a credit score, a financial identity, a payment, or an on-chain proof. Harvests remain off-chain records and show `Awaiting on-chain proof`; orders continue to show `Awaiting Solana transaction` until a future payment phase.

## Phase 4 prerequisites

A buyer wallet and farmer wallet must be connected on Devnet, order totals must be calculated and validated by the backend, a Devnet recipient address must be defined, and a wallet-approved transaction flow must be added before payment status can become `PAID`. Backend verification of the returned transaction signature must occur before recording payment evidence.
