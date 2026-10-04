import { useEffect, useState } from 'react';
import { ArrowUpRight, Bot, Check, CircleAlert, Clipboard, Copy, LockKeyhole, ShieldCheck, Sparkles, WalletCards } from 'lucide-react';
import { AppShell, PageFrame } from '../components/cropcred';
import { getPassport } from '../services/api';

export type Harvest = { crop: string; quantity: number; unit: string; date: string };
export type Order = { crop: string; amount: string; status: string };
export type AIAgentIntent = { action: string; crop: string; percentage: number; trigger: string; execution: 'USER_APPROVAL_REQUIRED' };
type PassportSnapshot = { verified_harvests: number; completed_sales: number; verified_payments: number; verified_deliveries: number; verified_trade_value: number; total_orders: number; credential?: { fingerprint?: string | null }; activity?: unknown[] };
type ProofRule = { id: string; label: string; metric: keyof PassportSnapshot; threshold: number; format: (value: number) => string };
type Proof = { id: string; commitment: string; condition: string; ruleId: string; threshold: number; eligible: boolean; generatedAt: string; recordCount: number; sourceFingerprint: string };

const proofRules: ProofRule[] = [
  { id: 'sales-100000', label: 'Verified sales greater than ₹1,00,000', metric: 'verified_trade_value', threshold: 100000, format: (value) => `₹${value.toLocaleString('en-IN')}` },
  { id: 'sales-250000', label: 'Verified sales greater than ₹2,50,000', metric: 'verified_trade_value', threshold: 250000, format: (value) => `₹${value.toLocaleString('en-IN')}` },
  { id: 'sales-500000', label: 'Verified sales greater than ₹5,00,000', metric: 'verified_trade_value', threshold: 500000, format: (value) => `₹${value.toLocaleString('en-IN')}` },
  { id: 'orders-3', label: 'At least 3 completed orders', metric: 'completed_sales', threshold: 3, format: (value) => `${value} completed orders` },
  { id: 'deliveries-3', label: 'At least 3 successful deliveries', metric: 'verified_deliveries', threshold: 3, format: (value) => `${value} successful deliveries` },
];

async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(hash)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

function metricValue(snapshot: PassportSnapshot, rule: ProofRule) { return Number(snapshot[rule.metric] || 0); }
function recordCount(snapshot: PassportSnapshot) { return Number(snapshot.verified_harvests || 0) + Number(snapshot.completed_sales || 0) + Number(snapshot.verified_payments || 0) + Number(snapshot.verified_deliveries || 0); }

export function ZKCreditDashboard() {
  const [snapshot, setSnapshot] = useState<PassportSnapshot | null>(null);
  const [selectedRule, setSelectedRule] = useState(proofRules[0].id);
  const [proof, setProof] = useState<Proof | null>(null);
  const [verifyState, setVerifyState] = useState<'idle' | 'checking' | 'valid' | 'invalid'>('idle');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const rule = proofRules.find((item) => item.id === selectedRule) || proofRules[0];

  useEffect(() => { getPassport().then(setSnapshot).catch((reason) => setError(reason instanceof Error ? reason.message : 'Economic Passport data could not be loaded.')); }, []);

  const generate = async () => {
    if (!snapshot) return;
    setBusy(true); setVerifyState('idle');
    const sourceFingerprint = snapshot.credential?.fingerprint || await sha256(JSON.stringify({ verified_harvests: snapshot.verified_harvests, completed_sales: snapshot.completed_sales, verified_payments: snapshot.verified_payments, verified_deliveries: snapshot.verified_deliveries, verified_trade_value: snapshot.verified_trade_value, total_orders: snapshot.total_orders, activityCount: snapshot.activity?.length || 0 }));
    const value = metricValue(snapshot, rule);
    const canonical = JSON.stringify({ sourceFingerprint, condition: rule.id, threshold: rule.threshold, metric: rule.metric, recordCount: recordCount(snapshot) });
    const commitment = await sha256(canonical);
    setProof({ id: `PEP-${commitment.slice(0, 12).toUpperCase()}`, commitment, condition: rule.label, ruleId: rule.id, threshold: rule.threshold, eligible: value >= rule.threshold, generatedAt: new Date().toISOString(), recordCount: recordCount(snapshot), sourceFingerprint });
    setBusy(false);
  };

  const verify = async () => {
    if (!proof || !snapshot) return;
    setVerifyState('checking');
    const sourceFingerprint = snapshot.credential?.fingerprint || await sha256(JSON.stringify({ verified_harvests: snapshot.verified_harvests, completed_sales: snapshot.completed_sales, verified_payments: snapshot.verified_payments, verified_deliveries: snapshot.verified_deliveries, verified_trade_value: snapshot.verified_trade_value, total_orders: snapshot.total_orders, activityCount: snapshot.activity?.length || 0 }));
    const expected = await sha256(JSON.stringify({ sourceFingerprint, condition: proof.ruleId, threshold: proof.threshold, metric: proofRules.find((item) => item.id === proof.ruleId)?.metric, recordCount: recordCount(snapshot) }));
    setVerifyState(expected === proof.commitment ? 'valid' : 'invalid');
  };

  const copy = async (value: string) => { await navigator.clipboard?.writeText(value); };
  return <section className="lab-card private-proof-card"><div className="lab-card-head"><div><div className="eyebrow">Private Economic Proof</div><h3>Prove activity without exposing transactions</h3><p>Prove that your verified economic activity meets a requirement without exposing individual transaction records.</p></div><LockKeyhole size={21} /></div><div className="prototype-label"><ShieldCheck size={14} /> Prototype — Cryptographic Commitment</div>{error ? <div className="lab-error"><CircleAlert size={15} />{error}</div> : !snapshot ? <div className="lab-loading"><Sparkles size={15} /> Loading verified Economic Passport aggregates…</div> : <><div className="lab-controls"><label>Proof condition<select value={selectedRule} onChange={(e) => { setSelectedRule(e.target.value); setProof(null); setVerifyState('idle'); }}>{proofRules.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><button className="button primary" onClick={generate} disabled={busy}>{busy ? 'Creating commitment…' : 'Generate private proof'} <Sparkles size={14} /></button></div>{proof && <div className="proof-result"><div className="proof-result-top"><div className={`proof-status ${proof.eligible ? 'eligible' : 'not-eligible'}`}><span>{proof.eligible ? <Check size={14} /> : <CircleAlert size={14} />}</span>{proof.eligible ? 'Eligible' : 'Not eligible'}</div><span className="proof-private"><LockKeyhole size={12} /> Private aggregates only</span></div><div className="proof-grid"><div><span>Proof ID</span><strong>{proof.id}</strong><button className="copy-button" onClick={() => copy(proof.id)} aria-label="Copy proof ID"><Copy size={13} /></button></div><div><span>Commitment / SHA-256</span><strong className="proof-hash">{proof.commitment}</strong><button className="copy-button" onClick={() => copy(proof.commitment)} aria-label="Copy commitment"><Clipboard size={13} /></button></div><div><span>Condition</span><strong>{proof.condition}</strong></div><div><span>Records used</span><strong>{proof.recordCount} verified records</strong></div><div><span>Generated</span><strong>{new Date(proof.generatedAt).toLocaleString('en-IN')}</strong></div></div><div className="proof-checks"><span><Check size={13} /> Proof generated</span><span><Check size={13} /> Data remains private</span><span><Check size={13} /> Cryptographic commitment created</span>{proof.eligible && <span><Check size={13} /> Condition satisfied</span>}</div><div className="verify-row"><button className="button outline" onClick={verify} disabled={verifyState === 'checking'}>{verifyState === 'checking' ? 'Checking locally…' : 'Verify proof locally'} <ShieldCheck size={14} /></button>{verifyState === 'valid' && <span className="verify-success"><Check size={14} /> Commitment matches current Passport data</span>}{verifyState === 'invalid' && <span className="verify-failure"><CircleAlert size={14} /> Verification failed — commitment does not match</span>}</div></div>}<small className="lab-note">This prototype is not a production zk-SNARK and is not currently verified on-chain. It never requests wallet signing or sends private economic records to an external service.</small></>}</section>;
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
  const [showRoadmap, setShowRoadmap] = useState(false);
  return <AppShell title="Innovation Lab" subtitle="Phase 1 · Safe presentation mode"><PageFrame><div className="page-intro"><div><div className="eyebrow">Private Economic Proof</div><h2>Prove a requirement, not a private history.</h2><p>Generate a local cryptographic commitment from your existing verified Economic Passport records.</p></div><span className="verified-chip"><ShieldCheck size={13} /> Prototype</span></div><div className="lab-banner"><ShieldCheck size={18} /><div><strong>Privacy-first, local verification</strong><span>Only verified aggregate records are used. Individual buyers, prices, dates, wallets, and transactions never appear in the proof result.</span></div></div><div className="lab-grid"><ZKCreditDashboard />{showRoadmap && <><AutonomousAgentPanel /><HarvestFuturesLaunchpad /></>}</div><div className="lab-toggle"><button className="button outline" onClick={() => setShowRoadmap(!showRoadmap)}>{showRoadmap ? 'Focus on Private Economic Proof' : 'Show other roadmap concepts'}</button></div><div className="info-strip"><div className="info-strip-icon"><ShieldCheck size={18} /></div><div><strong>Existing Solana functionality is unchanged.</strong><span>Real payments continue to use explicit wallet approval, Solana Devnet confirmation, exact lamport checks, and backend-independent verification.</span></div></div></PageFrame></AppShell>;
}
