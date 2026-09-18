import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { App as CapacitorApp } from '@capacitor/app';
import { SplashScreen } from '@capacitor/splash-screen';
import App from './App';
import './index.css';
import { SolanaWalletProvider } from './contexts/SolanaWalletContext';

function NativeLifecycle() {
  useEffect(() => {
    let removeBack: (() => void) | undefined;
    CapacitorApp.addListener('backButton', ({ canGoBack }) => {
      if (canGoBack && window.history.length > 1) window.history.back();
      else CapacitorApp.exitApp();
    }).then((handle) => { removeBack = () => handle.remove(); });
    SplashScreen.hide().catch(() => undefined);
    return () => { removeBack?.(); };
  }, []);
  return null;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SolanaWalletProvider>
      <NativeLifecycle />
      <App />
    </SolanaWalletProvider>
  </React.StrictMode>,
);
