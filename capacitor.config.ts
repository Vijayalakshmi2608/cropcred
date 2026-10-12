import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.cropcred.passport',
  appName: 'CropCred',
  webDir: 'dist/public',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'https',
    cleartext: false,
  },
  android: {
    // MWA's official browser transport uses ws://localhost after the wallet
    // app returns. Capacitor otherwise blocks this mixed-content association.
    allowMixedContent: true,
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#10201f',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#10201f',
    },
  },
};

export default config;
