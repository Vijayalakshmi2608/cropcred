import { useMemo, useState } from 'react';
import { ArrowUpRight, Bot, Check, CircleAlert, LockKeyhole, ShieldCheck, Sparkles, WalletCards } from 'lucide-react';
import { AppShell, PageFrame, SectionHeading } from '../components/cropcred';

export type Harvest = { crop: string; quantity: number; unit: string; date: string };
export type Order = { crop: string; amount: string; status: string };
export type ZKProof = { id: string; threshold: number; commitment: string; status: 'DEMO_ONLY' };
export type AIAgentIntent = { action: string; crop: string; percentage: number; trigger: string; execution: 'USER_APPROVAL_REQUIRED' };

const demoHarvests: Harvest[] = [
  { crop: 'Tomatoes', quantity: 420, unit: 'kg', date: '05 Sep 2026' },
  { crop: 'Rice', quantity: 500, unit: 'kg', date: '18 Sep 2026' },
];
const demoOrders: Order[] = [
  { crop: 'Tomatoes', amount: '₹14,700', status: 'Payment verified' },
  { crop: 'Rice', amount: '₹18,200', status: 'Delivery confirmed' },
];

async function digest(value: string) {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(hash)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function ZKCreditDashboard({ harvests, orders }: { harvests: Harvest[]; orders: Order[] }) {
  const [threshold, setThreshold] = useState(5000);
  const [proof, setProof] = useState<ZKProof | null>(null);
  const [busy, setBusy] = useState(false);
  const total = orders.reduce((sum, order) => sum + Number(order.amount.replace(/[^0-9.]/g, '')), 0);
  const generate = async () => {
    setBusy(true);
    const commitment = await digest(JSON.stringify({ threshold, total, harvestCount: harvests.length }));
    setProof({ id: `ZK-DEMO-${commitment.slice(0, 10).toUpperCase()}`, threshold, commitment, status: 'DEMO_ONLY' });
    setBusy(false);
  };
  return <section className="lab-card"><div className="lab-card-head"><div><div className="eyebrow">Private credit identity</div><h3>Generate a private credit proof</h3><p>Creates a local commitment from demo records. This build does not claim a zk-SNARK or network verification.</p></div><LockKeyhole size={21} /></div><div className="lab-controls"><label>Verified sales threshold<select value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}><option value="5000">₹5,000</option><option value="10000">₹10,000</option><option value="25000">₹25,000</option></select></label><button className="button primary" onClick={generate} disabled={busy}>{busy ? 'Hashing locally…' : 'Generate demo proof'} <Sparkles size={14} /></button></div>{proof && <div className="lab-result"><Check size={16} /><div><strong>{proof.id}</strong><span>Commitment {proof.commitment.slice(0, 20)}… · {proof.status.replace('_', ' ')}</span></div></div>}<small className="lab-note">No buyer addresses, dates, or unit prices are shared. A production ZK circuit and verifier are not included.</small></section>;
}

export function AutonomousAgentPanel() {
  const [instruction, setInstruction] = useState('Auto-sell 80% of my tomato yield when the target price is reached.');
  const [intent, setIntent] = useState<AIAgentIntent | null>(null);
  const parse = () => setIntent({ action: 'CREATE_MARKETPLACE_INTENT', crop: instruction.toLowerCase().includes('tomato') ? 'Tomatoes' : 'Crop supply', percentage: Number(instruction.match(/(\d+)%/)?.[1] || 80), trigger: 'Target price reached', execution: 'USER_APPROVAL_REQUIRED' });
  return <section className="lab-card"><div className="lab-card-head"><div><div className="eyebrow">CropAgent · presentation mode</div><h3>Turn intent into a reviewable action</h3><p>Natural language is converted locally into a preview. No private keys, session keys, or autonomous signing are enabled.</p></div><Bot size={21} /></div><textarea className="lab-input" value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={3} aria-label="CropAgent instruction" /><div className="lab-actions"><button className="button outline" onClick={parse}>Preview structured intent <ArrowUpRight size={14} /></button>{intent && <span className="lab-approval"><CircleAlert size={14} /> Approval required before any Devnet transaction</span>}</div>{intent && <pre className="lab-code">{JSON.stringify(intent, null, 2)}</pre>}</section>;
}

export function HarvestFuturesLaunchpad() {
  return <section className="lab-card"><div className="lab-card-head"><div><div className="eyebrow">Harvest Yield Futures · roadmap</div><h3>Future revenue launchpad</h3><p>Campaign discovery is shown as a product concept only. Token minting, fractional sales, lending, and revenue contracts are disabled.</p></div><WalletCards size={21} /></div><div className="lab-launchpad"><div><strong>Forward Harvest NFT</strong><span>Design review · not minted</span></div><div><strong>Investor marketplace</strong><span>Not open · no funds accepted</span></div><div><strong>Settlement schedule</strong><span>Requires audited Solana program</span></div></div><small className="lab-note">CropCred does not claim that a token proves physical crop existence, quality, or quantity.</small></section>;
}

export default function HackathonLab() {
  const harvests = useMemo(() => demoHarvests, []);
  const orders = useMemo(() => demoOrders, []);
  return <AppShell title="Hackathon Lab" subtitle="Safe presentation mode · Solana Devnet"><PageFrame><div className="page-intro"><div><div className="eyebrow">Experimental surfaces</div><h2>Show the roadmap without overclaiming.</h2><p>These demos are isolated from real payments. Existing wallet connection and settlement remain strictly Solana Devnet with explicit user approval.</p></div><span className="verified-chip"><ShieldCheck size={13} /> Demo mode</span></div><div className="lab-banner"><ShieldCheck size={18} /><div><strong>Safe by default</strong><span>Local hashing and intent previews only. No token issuance, autonomous signing, or fake blockchain confirmations.</span></div></div><div className="lab-grid"><ZKCreditDashboard harvests={harvests} orders={orders} /><AutonomousAgentPanel /><HarvestFuturesLaunchpad /></div><div className="info-strip"><div className="info-strip-icon"><ShieldCheck size={18} /></div><div><strong>Real settlement remains unchanged.</strong><span>When a buyer pays, the existing flow still uses wallet approval, Solana Devnet confirmation, exact lamport checks, and backend-independent verification.</span></div></div></PageFrame></AppShell>;
}
