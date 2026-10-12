import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';
import { Connection, PublicKey, LAMPORTS_PER_SOL } from '@solana/web3.js';
import { SolanaMobileWalletAdapter, createDefaultAddressSelector, createDefaultAuthorizationResultCache } from '@solana-mobile/wallet-adapter-mobile';
import { updateFarmerWallet } from '../services/api';
import { getDevnetRpcUrl } from '../services/solanaPayment';

type BrowserWalletProvider = { isPhantom?: boolean; isConnected?: boolean; publicKey?: { toString(): string }; network?: string; connect: () => Promise<{ publicKey?: { toString(): string }}>; disconnect: () => Promise<void>; signAndSendTransaction?: (transaction: any) => Promise<{ signature: string }>; on?: (event: string, callback: (...args: any[]) => void) => void; off?: (event: string, callback: (...args: any[]) => void) => void };

declare global { interface Window { solana?: BrowserWalletProvider; } }

type WalletContextValue = { connected: boolean; publicKey: string | null; walletName: string | null; network: 'devnet' | 'wrong-network' | 'unknown'; balance: number | null; connecting: boolean; message: string | null; connect: () => Promise<void>; disconnect: () => Promise<void>; copyAddress: () => Promise<boolean>; refreshBalance: () => Promise<void>; sendTransaction: (transaction: any, connection: Connection) => Promise<string>; clearMessage: () => void; };
const SolanaWalletContext = createContext<WalletContextValue | null>(null);
const STORAGE_KEY = 'cropcred-wallet-address';

export function SolanaWalletProvider({ children }: { children: ReactNode }) {
  const [publicKey, setPublicKey] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [balance, setBalance] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const native = Capacitor.isNativePlatform();
  const browserProvider = window.solana;
  const nativeAdapter = useMemo(() => new SolanaMobileWalletAdapter({
    addressSelector: createDefaultAddressSelector(),
    appIdentity: { name: 'CropCred', uri: import.meta.env.VITE_APP_URL || 'https://cropcred.app', icon: '/icon.svg' },
    authorizationResultCache: createDefaultAuthorizationResultCache(),
    cluster: 'devnet',
    onWalletNotFound: async () => { setMessage('No compatible Solana wallet found. Install Phantom or another Mobile Wallet Adapter wallet.'); },
  }), []);
  const activeProvider = native ? nativeAdapter : browserProvider;
  const network: WalletContextValue['network'] = native ? 'devnet' : browserProvider?.network && browserProvider.network !== 'devnet' ? 'wrong-network' : 'devnet';

  const persist = useCallback(async (address: string | null) => {
    if (address) {
      localStorage.setItem(STORAGE_KEY, address);
      try { await updateFarmerWallet('farmer-01', address); } catch { /* preserve local wallet state if API is unavailable */ }
    } else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const refreshBalance = useCallback(async () => {
    if (!publicKey || network !== 'devnet') return;
    try { const connection = new Connection(getDevnetRpcUrl(), 'confirmed'); setBalance((await connection.getBalance(new PublicKey(publicKey))) / LAMPORTS_PER_SOL); }
    catch { setBalance(null); }
  }, [network, publicKey]);

  const readNativeAddress = useCallback(() => {
    const adapter = nativeAdapter as any;
    return adapter.publicKey?.toString?.() || adapter.accounts?.[0]?.address || null;
  }, [nativeAdapter]);

  const syncNativeWallet = useCallback(async () => {
    if (!native) return;
    const address = readNativeAddress();
    if (address) {
      setPublicKey(address);
      setConnected(true);
      await persist(address);
      await refreshBalance();
    } else if (!nativeAdapter.connected) {
      setConnected(false);
    }
  }, [native, nativeAdapter, persist, readNativeAddress, refreshBalance]);

  const connect = useCallback(async () => {
    if (!activeProvider) { setMessage('Please install or unlock a compatible Solana wallet.'); return; }
    if (connecting) return;
    setConnecting(true); setMessage(null);
    try {
      if (native) {
        await nativeAdapter.connect();
        const address = readNativeAddress();
        if (!address) throw new Error('No public address returned');
        setPublicKey(address); setConnected(true); await persist(address); setMessage('Wallet connected on Solana Devnet.');
      } else {
        const response = await browserProvider!.connect();
        const address = response.publicKey?.toString() || browserProvider!.publicKey?.toString();
        if (!address) throw new Error('No public address returned');
        if (browserProvider!.network && browserProvider!.network !== 'devnet') { setMessage('Please switch your wallet to Solana Devnet.'); setConnecting(false); return; }
        setPublicKey(address); setConnected(true); await persist(address); setMessage('Wallet connected on Solana Devnet.');
      }
    } catch (error: any) {
      const cancelled = error?.code === 4001 || /reject|cancel/i.test(String(error?.message || ''));
      setMessage(cancelled ? 'Wallet connection was cancelled.' : error?.message || 'Wallet connection could not be completed.');
    } finally { setConnecting(false); }
  }, [activeProvider, browserProvider, connecting, native, nativeAdapter, persist, readNativeAddress]);

  const disconnect = useCallback(async () => {
    try { await activeProvider?.disconnect(); } finally { setConnected(false); setPublicKey(null); setBalance(null); await persist(null); setMessage('Wallet disconnected.'); }
  }, [activeProvider, persist]);

  const sendTransaction = useCallback(async (transaction: any, connection: Connection) => {
    if (native) return nativeAdapter.sendTransaction(transaction, connection, { preflightCommitment: 'confirmed' });
    if (!browserProvider?.signAndSendTransaction) throw new Error('Your wallet does not support Devnet transaction approval.');
    return (await browserProvider.signAndSendTransaction(transaction)).signature;
  }, [browserProvider, native, nativeAdapter]);

  const copyAddress = useCallback(async () => { if (!publicKey) return false; await navigator.clipboard?.writeText(publicKey); setMessage('Wallet address copied.'); return true; }, [publicKey]);

  useEffect(() => { if (publicKey && activeProvider) { setConnected(native ? nativeAdapter.connected : Boolean(browserProvider?.isConnected || browserProvider?.publicKey)); refreshBalance(); } }, [activeProvider, browserProvider, native, nativeAdapter, publicKey, refreshBalance]);
  useEffect(() => {
    if (!native) return;
    let disposed = false;
    const resume = () => { if (!disposed) void syncNativeWallet(); };
    const appState = App.addListener('appStateChange', ({ isActive }) => { if (isActive) resume(); });
    window.addEventListener('focus', resume);
    document.addEventListener('visibilitychange', resume);
    return () => {
      disposed = true;
      void appState.then(listener => listener.remove());
      window.removeEventListener('focus', resume);
      document.removeEventListener('visibilitychange', resume);
    };
  }, [native, syncNativeWallet]);
  useEffect(() => {
    if (!activeProvider?.on) return;
    const onAccountChanged = (key: any) => { const address = key?.toString?.() || nativeAdapter.publicKey?.toString() || null; setPublicKey(address); setConnected(Boolean(address)); persist(address); };
    const onConnect = () => { const address = native ? readNativeAddress() : browserProvider?.publicKey?.toString() || null; if (address) { setPublicKey(address); setConnected(true); void persist(address); } };
    const onDisconnect = () => { setPublicKey(null); setConnected(false); setBalance(null); localStorage.removeItem(STORAGE_KEY); setMessage('Wallet disconnected.'); };
    const providerEvents = activeProvider as any;
    if (!native) providerEvents.on('accountChanged', onAccountChanged);
    providerEvents.on('connect', onConnect); providerEvents.on('disconnect', onDisconnect);
    return () => { if (!native) providerEvents.off?.('accountChanged', onAccountChanged); providerEvents.off?.('connect', onConnect); providerEvents.off?.('disconnect', onDisconnect); };
  }, [activeProvider, browserProvider, native, nativeAdapter, persist, readNativeAddress]);

  const value = useMemo(() => ({ connected, publicKey, walletName: native ? (connected ? 'Mobile wallet' : null) : browserProvider?.isPhantom ? 'Phantom' : publicKey ? 'Solana wallet' : null, network, balance, connecting, message, connect, disconnect, copyAddress, refreshBalance, sendTransaction, clearMessage: () => setMessage(null) }), [balance, browserProvider, connect, connected, connecting, copyAddress, disconnect, native, network, publicKey, refreshBalance, sendTransaction, message]);
  return <SolanaWalletContext.Provider value={value}>{children}</SolanaWalletContext.Provider>;
}

export function useSolanaWallet() { const value = useContext(SolanaWalletContext); if (!value) throw new Error('useSolanaWallet must be used within SolanaWalletProvider'); return value; }
