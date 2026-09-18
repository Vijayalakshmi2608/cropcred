# CropCred Android APK

CropCred now ships as a Capacitor Android application without removing the existing React/Vite routes or Flask integration. The Android shell uses the existing UI bundle, Capacitor App lifecycle handling for the Android back button, Capacitor Splash Screen and Status Bar plugins, CropCred launcher branding, and Solana Mobile Wallet Adapter for native Android wallet authorization.

## Configure the production API before building

The APK must be built with an HTTPS backend URL. Do not ship the default localhost value. Set the production API and optional Solana RPC endpoint in the shell environment before running the mobile build:

```bash
export VITE_API_URL="https://api.example.com/api"
export VITE_SOLANA_RPC_URL="https://api.devnet.solana.com"
export VITE_APP_URL="https://app.example.com"
```

The Flask API must allow the APK origin and expose the existing `/api` routes for wallet association, payment intent creation, independent payment verification, Passport updates, and credential verification. The mobile client never stores seed phrases or private keys.

## Build the debug APK

From the project root:

```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export ANDROID_HOME=/home/ubuntu/android-sdk
export ANDROID_SDK_ROOT=/home/ubuntu/android-sdk
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

pnpm mobile:apk
```

The repeatable scripts are:

```bash
pnpm mobile:sync   # build the web bundle and sync Capacitor Android assets
pnpm mobile:apk    # sync and assemble the debug APK
pnpm mobile:open   # open the native project in Android Studio
```

The debug APK is signed with the Android debug keystore and is suitable for direct installation on a development device. A release Play Store artifact requires a separately managed release keystore and signing configuration; no production signing key is stored in this repository.

## Install on an Android device

Enable Developer Options and USB debugging on the device, connect it to the build machine, then verify it appears:

```bash
adb devices -l
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

Open **CropCred** from the launcher. To uninstall:

```bash
adb uninstall com.cropcred.passport
```

## Wallet and payment behavior

On Android, the app uses the Solana Mobile Wallet Adapter with a Devnet cluster configuration. Install Phantom or another compatible Solana mobile wallet before tapping **Connect Wallet**. The app handles wallet-not-found, cancellation, disconnect, account changes, balance refresh, and wrong-network states. The wallet signs the transaction; CropCred never receives or stores a seed phrase or private key.

Payment remains a real native SOL transfer on Solana Devnet:

> **Solana Devnet — Test Network — No Real Monetary Value**

The order value remains in INR. The separate settlement amount is a small Devnet SOL amount returned by the backend payment intent. After explicit wallet approval, the client confirms the signature on Devnet and sends it to Flask. The backend independently verifies the payer, recipient, amount, network, and transaction signature before marking the order `PAID`, refreshing the Economic Passport, updating the Economic Credential, and showing the Solana Explorer link.

## Device test checklist

Use a real Android device with a compatible wallet and Devnet funds. Verify: app launch and branded splash; Android back navigation; API loading from the configured HTTPS URL; wallet connect and public address display; Devnet balance; account change and disconnect; wallet rejection; missing wallet; wrong-network messaging; order creation; exact INR/SOL separation; explicit transaction approval; confirmed Devnet signature; backend payment verification; Passport update; Credential verification; and Solana Explorer navigation.

The sandbox used for this build does not expose a physical Android device or emulator through ADB, so APK compilation and artifact verification were completed here, while the device-only wallet approval loop must be run on a connected Android device with Phantom or another compatible wallet.
