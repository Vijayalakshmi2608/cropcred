# Physical-device validation checklist

Target: OPPO F9 / Android device

## Pending device actions

- [ ] Uninstall the previous CropCred APK.
- [ ] Install the current GitHub release APK.
- [ ] Confirm the device has internet access and Phantom is installed/unlocked.
- [ ] In Phantom, switch to Solana Devnet and obtain Devnet SOL.
- [ ] Tap CropCred **Connect Wallet**.
- [ ] Approve the native Mobile Wallet Adapter request in Phantom.
- [ ] Return to CropCred and verify the actual public key is displayed.
- [ ] Disconnect and reconnect; confirm state is cleared and recreated correctly.
- [ ] Create harvest → linked batch/listing → marketplace order.
- [ ] Start payment intent and confirm the recipient/amount shown by CropCred.
- [ ] Approve the real Devnet SOL transfer in Phantom.
- [ ] Confirm the transaction on Devnet and verify the backend marks the order paid.
- [ ] Confirm Passport payment evidence and Devnet Explorer link.
- [ ] Test wallet rejection, cancellation, app background/resume, missing wallet, and insufficient Devnet SOL.

## Not claimed by this repository audit

No physical OPPO F9 installation, Phantom handoff, or live Devnet settlement was performed in the sandbox. These remain explicit device-side validation items.
