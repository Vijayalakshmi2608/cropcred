import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Connection, PublicKey, clusterApiUrl, LAMPORTS_PER_SOL } from '@solana/web3.js';
import { updateFarmerWallet } from '../services/api';

type WalletProvider = { isPhantom?: boolean; isConnected?: boolean; publicKey?: { toString(): string }; network?: string; connect: () => Promise<{ publicKey?: { toString(): string }}>; disconnect: () => Promise<void>; signAndSendTransaction?: (transaction: any) => Promise<{ signature: string }>; on?: (event: string, callback: (...args: any[]) => void) => void; off?: (event: string, callback: (...args: any[]) => void) => void };

declare global { interface Window { solana?: WalletProvider; } }

type WalletContextValue = { connected: boolean; publicKey: string | null; walletName: string | null; network: 'devnet' | 'wrong-network' | 'unknown'; balance: number | null; connecting: boolean; message: string | null; connect: () => Promise<void>; disconnect: () => Promise<void>; copyAddress: () => Promise<boolean>; refreshBalance: () => Promise<void>; clearMessage: () => void; };
const SolanaWalletContext = createContext<WalletContextValue | null>(null);
const STORAGE_KEY = 'cropcred-wallet-address';

export function SolanaWalletProvider({ children }: { children: ReactNode }) {
  const [publicKey, setPublicKey] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [balance, setBalance] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const provider = window.solana;
  const network: WalletContextValue['network'] = provider?.network && provider.network !== 'devnet' ? 'wrong-network' : 'devnet';

  const persist = useCallback(async (address: string | null) => {
    if (address) {
      localStorage.setItem(STORAGE_KEY, address);
      try { await updateFarmerWallet('farmer-01', address); } catch { /* preserve local wallet state if API is unavailable */ }
    } else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const refreshBalance = useCallback(async () => {
    if (!publicKey || network !== 'devnet') return;
    try { const connection = new Connection(clusterApiUrl('devnet'), 'confirmed'); setBalance((await connection.getBalance(new PublicKey(publicKey))) / LAMPORTS_PER_SOL); }
    catch { setBalance(null); }
  }, [network, publicKey]);

  const connect = useCallback(async () => {
    if (!provider) { setMessage('Please install or unlock a compatible Solana wallet.'); return; }
    setConnecting(true); setMessage(null);
    try {
      const response = await provider.connect();
      const address = response.publicKey?.toString() || provider.publicKey?.toString();
      if (!address) throw new Error('No public address returned');
      if (provider.network && provider.network !== 'devnet') { setMessage('Please switch your wallet to Solana Devnet.'); setConnecting(false); return; }
      setPublicKey(address); setConnected(true); await persist(address); setMessage('Wallet connected on Solana Devnet.');
    } catch (error: any) {
      setMessage(error?.code === 4001 ? 'Wallet connection was cancelled.' : 'Wallet connection could not be completed.');
    } finally { setConnecting(false); }
  }, [persist, provider]);

  const disconnect = useCallback(async () => {
    try { await provider?.disconnect(); } finally { setConnected(false); setPublicKey(null); setBalance(null); await persist(null); setMessage('Wallet disconnected.'); }
  }, [persist, provider]);

  const copyAddress = useCallback(async () => { if (!publicKey) return false; await navigator.clipboard?.writeText(publicKey); setMessage('Wallet address copied.'); return true; }, [publicKey]);

  useEffect(() => { if (publicKey && provider) { setConnected(true); refreshBalance(); } }, [publicKey, provider, refreshBalance]);
  useEffect(() => {
    if (!provider?.on) return;
    const onAccountChanged = (key: any) => { const address = key?.toString?.() || null; setPublicKey(address); setConnected(Boolean(address)); persist(address); };
    const onDisconnect = () => { setPublicKey(null); setConnected(false); setBalance(null); localStorage.removeItem(STORAGE_KEY); setMessage('Wallet disconnected.'); };
    provider.on('accountChanged', onAccountChanged); provider.on('disconnect', onDisconnect);
    return () => { provider.off?.('accountChanged', onAccountChanged); provider.off?.('disconnect', onDisconnect); };
  }, [persist, provider]);

  const value = useMemo(() => ({ connected, publicKey, walletName: provider?.isPhantom ? 'Phantom' : publicKey ? 'Solana wallet' : null, network, balance, connecting, message, connect, disconnect, copyAddress, refreshBalance, clearMessage: () => setMessage(null) }), [balance, connect, connected, connecting, copyAddress, disconnect, message, network, publicKey, provider, refreshBalance]);
  return <SolanaWalletContext.Provider value={value}>{children}</SolanaWalletContext.Provider>;
}

export function useSolanaWallet() { const value = useContext(SolanaWalletContext); if (!value) throw new Error('useSolanaWallet must be used within SolanaWalletProvider'); return value; }
