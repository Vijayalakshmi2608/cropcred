import { Connection, LAMPORTS_PER_SOL, PublicKey, SystemProgram, Transaction, clusterApiUrl } from '@solana/web3.js';

const DEVNET = 'devnet';
export const DEMO_SETTLEMENT_SOL = 0.001;
export const DEVNET_WARNING = 'Solana Devnet — Test Network — No Real Monetary Value';

export function getDevnetRpcUrl() {
  const configured = String(import.meta.env.VITE_SOLANA_RPC_URL || '').trim();
  const url = configured || clusterApiUrl('devnet');
  let hostname = '';
  try { hostname = new URL(url).hostname.toLowerCase(); } catch { throw new Error('The Solana RPC endpoint is invalid. CropCred requires Solana Devnet.'); }
  if (!hostname.includes('devnet') || hostname.includes('mainnet') || hostname.includes('localhost') || hostname === '127.0.0.1') throw new Error('CropCred only supports a Solana Devnet RPC endpoint.');
  return url;
}

export function getDevnetConnection() { return new Connection(getDevnetRpcUrl(), 'confirmed'); }
export function getExplorerUrl(signature: string) { return `https://explorer.solana.com/tx/${signature}?cluster=devnet`; }
export function validateDevnetWallet(publicKey: string | null) { if (!publicKey) throw new Error('Connect your Solana wallet to continue.'); try { return new PublicKey(publicKey); } catch { throw new Error('The connected wallet address is invalid.'); } }

export async function sendDevnetPayment({ payer, recipient, amountSol = DEMO_SETTLEMENT_SOL, signAndSendTransaction, onState }: { payer: string; recipient: string; amountSol?: number; signAndSendTransaction?: (transaction: Transaction, connection: Connection) => Promise<string>; onState?: (state: string) => void }) {
  const payerKey = validateDevnetWallet(payer); let recipientKey: PublicKey;
  try { recipientKey = new PublicKey(recipient); } catch { throw new Error('This seller has not connected a settlement wallet yet.'); }
  if (amountSol <= 0 || amountSol > 1) throw new Error('Invalid Devnet settlement amount.');
  const provider = window.solana;
  if (!signAndSendTransaction && (!provider?.connect || !provider.signAndSendTransaction)) throw new Error('Your wallet does not support Devnet transaction approval.');
  onState?.('CREATING');
  const connection = getDevnetConnection();
  const transaction = new Transaction().add(SystemProgram.transfer({ fromPubkey: payerKey, toPubkey: recipientKey, lamports: Math.round(amountSol * LAMPORTS_PER_SOL) }));
  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');
  transaction.recentBlockhash = blockhash; transaction.feePayer = payerKey;
  onState?.('AWAITING_WALLET_APPROVAL');
  const signature = signAndSendTransaction ? await signAndSendTransaction(transaction, connection) : (await provider!.signAndSendTransaction!(transaction)).signature;
  onState?.('SUBMITTING');
  await connection.confirmTransaction({ signature, blockhash, lastValidBlockHeight }, 'confirmed');
  onState?.('CONFIRMING');
  return { signature, explorerUrl: getExplorerUrl(signature), amountSol, network: DEVNET };
}
