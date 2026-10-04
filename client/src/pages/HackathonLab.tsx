import { useEffect, useState } from 'react';
import { ArrowUpRight, Bot, Check, CircleAlert, Clipboard, Copy, LockKeyhole, ShieldCheck, Sparkles, WalletCards } from 'lucide-react';
import { AppShell, PageFrame } from '../components/cropcred';
import type { Demand, Listing, Harvest as HarvestRecord } from '../data/mockData';
import { getDemands, getHarvests, getMarketplaceListings } from '../services/api';
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

type ParsedIntent = { crop: string; percentage: number; priceTrigger: number | null; action: 'SELL'; conditions: string[] };
type AgentMatch = { id: string; kind: 'MARKETPLACE' | 'B2B_DEMAND'; buyer: string; crop: string; quantity: string; price: string; reason: string; listing?: Listing; demand?: Demand };

function parseIntent(text: string, knownCrops: string[]): ParsedIntent {
  const lower = text.toLowerCase();
  const matchedCrop = knownCrops.find((crop) => lower.includes(crop.toLowerCase())) || 'Unspecified crop';
  const percentage = Math.max(1, Math.min(100, Number(text.match(/(\d{1,3})\s*%/)?.[1] || 100)));
  const priceTrigger = text.match(/₹\s*([\d,]+)(?:\s*\/\s*[a-z]+)?/i);
  return { crop: matchedCrop, percentage, priceTrigger: priceTrigger ? Number(priceTrigger[1].replace(/,/g, '')) : null, action: 'SELL', conditions: [/verified buyer/i.test(text) ? 'Verified buyer required' : 'Buyer match required', priceTrigger ? 'Price trigger detected' : 'Price trigger not specified'] };
}

function priceNumber(value: string) { const match = value.replace(/,/g, '').match(/₹\s*([\d.]+)/); return match ? Number(match[1]) : null; }

export function AutonomousAgentPanel({ onOrderCreated }: { onOrderCreated: (listing: Listing, quantity?: number) => Promise<void> }) {
  const [instruction, setInstruction] = useState('Sell 80% of my tomato harvest if a verified buyer offers ₹15/kg.');
  const [intent, setIntent] = useState<ParsedIntent | null>(null);
  const [matches, setMatches] = useState<AgentMatch[]>([]);
  const [selected, setSelected] = useState<AgentMatch | null>(null);
  const [approval, setApproval] = useState(false);
  const [status, setStatus] = useState<'idle' | 'parsing' | 'matching' | 'confirm' | 'submitting' | 'success' | 'error'>('idle');
  const [error, setError] = useState('');
  const parseAndMatch = async () => {
    setStatus('parsing'); setError(''); setSelected(null); setApproval(false);
    const [listings, demands] = await Promise.all([getMarketplaceListings(), getDemands()]).catch((reason) => { setError(reason instanceof Error ? reason.message : 'Marketplace data could not be loaded.'); setStatus('error'); return [[], []] as [Listing[], Demand[]]; });
    if (!listings.length && !demands.length) { setError('No live marketplace or B2B demand records matched the request.'); setStatus('error'); return; }
    const parsed = parseIntent(instruction, [...listings.map((item) => item.crop), ...demands.map((item) => item.crop)].filter((value, index, all) => all.indexOf(value) === index));
    setIntent(parsed); setStatus('matching');
    const crop = parsed.crop.toLowerCase();
    const listingMatches: AgentMatch[] = listings.filter((item) => item.available > 0 && (parsed.crop === 'Unspecified crop' || item.crop.toLowerCase().includes(crop))).map((item) => {
      const price = priceNumber(item.price);
      const priceReason = parsed.priceTrigger === null ? 'No price ceiling specified' : price !== null && price >= parsed.priceTrigger ? `Listed at ₹${price}/${item.unit}, meeting the ₹${parsed.priceTrigger} trigger` : `Listed at ${item.price}; review against the ₹${parsed.priceTrigger} trigger`;
      return { id: item.listingId, kind: 'MARKETPLACE', buyer: 'CropCred marketplace preorder', crop: item.crop, quantity: `${item.available} ${item.unit}`, price: item.price, reason: `${item.verification}; ${priceReason}`, listing: item };
    });
    const demandMatches: AgentMatch[] = demands.filter((item) => parsed.crop === 'Unspecified crop' || item.crop.toLowerCase().includes(crop)).map((item) => ({ id: item.id, kind: 'B2B_DEMAND', buyer: item.buyer, crop: item.crop, quantity: item.quantity, price: item.price, reason: `B2B ${item.buyerType.toLowerCase()} demand in ${item.location}; respond in Demand Network to make an offer`, demand: item }));
    setMatches([...listingMatches, ...demandMatches]); setStatus('confirm');
  };
  const approve = async () => {
    if (!selected?.listing || !approval) return;
    setStatus('submitting'); setError('');
    try { const quantity = Math.max(1, Math.round(selected.listing.available * ((intent?.percentage || 100) / 100))); await onOrderCreated(selected.listing, quantity); setStatus('success'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The approved order could not be created.'); setStatus('error'); }
  };
  return <section className="lab-card cropagent-card"><div className="lab-card-head"><div><div className="eyebrow">CropAgent · AI-assisted / Human-approved</div><h3>Turn a selling intention into a reviewed order</h3><p>Type a natural-language intention. CropAgent parses it locally, matches live CropCred records, and waits for your approval.</p></div><Bot size={21} /></div><textarea className="lab-input" value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={3} aria-label="CropAgent selling intention" /><div className="lab-actions"><button className="button outline" onClick={parseAndMatch} disabled={status === 'parsing' || status === 'matching'}>{status === 'parsing' ? 'Parsing intention…' : status === 'matching' ? 'Matching live records…' : 'Parse and find matches'} <ArrowUpRight size={14} /></button><span className="lab-approval"><CircleAlert size={14} /> No autonomous signing</span></div>{intent && <div className="intent-card"><div className="eyebrow">Step 1 · Parsed intent</div><div className="intent-grid"><div><span>Action</span><strong>{intent.action}</strong></div><div><span>Crop</span><strong>{intent.crop}</strong></div><div><span>Quantity</span><strong>{intent.percentage}% of available supply</strong></div><div><span>Price trigger</span><strong>{intent.priceTrigger ? `₹${intent.priceTrigger}/unit` : 'Not specified'}</strong></div></div><div className="intent-conditions">{intent.conditions.map((condition) => <span key={condition}><Check size={12} /> {condition}</span>)}</div></div>}{status === 'confirm' && <div className="agent-matches"><div className="eyebrow">Step 2 · Live matches</div>{matches.length ? matches.map((match) => <div className={`agent-match ${selected?.id === match.id ? 'selected' : ''}`} key={match.id}><div><strong>{match.buyer}</strong><span>{match.crop} · {match.quantity} · {match.price}</span><small><ShieldCheck size={12} /> {match.reason}</small></div>{match.listing ? <button className="button outline" onClick={() => { setSelected(match); setApproval(false); }}>Select offer</button> : <span className="match-context">B2B context</span>}</div>) : <div className="lab-loading">No matching live records found.</div>}</div>}{selected?.listing && <div className="agent-confirm"><div className="eyebrow">Step 3 · Final confirmation</div><h4>Review before creating the order</h4><p><strong>{intent?.percentage}%</strong> of <strong>{selected.listing.crop}</strong> supply will be sent to the existing marketplace order flow for <strong>{selected.buyer}</strong>.</p><label className="approval-check"><input type="checkbox" checked={approval} onChange={(e) => setApproval(e.target.checked)} /> I reviewed this order and explicitly approve creating it. Wallet payment approval will happen later in the existing Solana Devnet flow.</label><button className="button primary" onClick={approve} disabled={!approval || status === 'submitting'}>{status === 'submitting' ? 'Creating approved order…' : 'Approve and create order'} <Check size={14} /></button></div>}{status === 'success' && <div className="agent-success"><Check size={16} /><div><strong>Human-approved order created</strong><span>Continue to Orders to review the existing payment process. No blockchain transaction was signed automatically.</span></div></div>}{error && <div className="lab-error"><CircleAlert size={15} />{error}</div>}<small className="lab-note">CropAgent is a review-only assistant. It does not access private keys, use session keys, sign transactions, or claim autonomous execution.</small></section>;
}

type ForwardContract = { id: string; hash: string; crop: string; quantity: number; unit: string; harvestDate: string; price: number; condition: string; createdAt: string; farmer: string };

export function HarvestFuturesLaunchpad() {
  const [harvests, setHarvests] = useState<HarvestRecord[]>([]);
  const [passport, setPassport] = useState<any>(null);
  const [selectedId, setSelectedId] = useState('');
  const [form, setForm] = useState({ quantity: '', date: '', price: '', condition: 'After verified delivery confirmation' });
  const [contract, setContract] = useState<ForwardContract | null>(null);
  const [preview, setPreview] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => { Promise.all([getHarvests(), getPassport()]).then(([records, currentPassport]) => { const verified = records.filter((item) => item.status === 'VERIFIED'); setHarvests(verified); setPassport(currentPassport); if (verified[0]) { setSelectedId(verified[0].id); setForm({ quantity: String(verified[0].quantity), date: '', price: verified[0].price.replace(/[^0-9.]/g, ''), condition: 'After verified delivery confirmation' }); } }).catch((reason) => setError(reason instanceof Error ? reason.message : 'Verified harvest data could not be loaded.')).finally(() => setLoading(false)); }, []);
  const selected = harvests.find((item) => item.id === selectedId);
  const chooseHarvest = (id: string) => { const item = harvests.find((record) => record.id === id); setSelectedId(id); setContract(null); setPreview(false); if (item) setForm({ quantity: String(item.quantity), date: item.date, price: item.price.replace(/[^0-9.]/g, ''), condition: 'After verified delivery confirmation' }); };
  const createContract = async (event: React.FormEvent) => { event.preventDefault(); if (!selected || !form.quantity || !form.date || !form.price) return; const canonical = JSON.stringify({ farmer: selected.farmer, harvest: selected.id, crop: selected.crop, quantity: Number(form.quantity), unit: selected.unit, harvestDate: form.date, price: Number(form.price), condition: form.condition }); const hash = await sha256(canonical); setContract({ id: `FWD-${hash.slice(0, 12).toUpperCase()}`, hash, crop: selected.crop, quantity: Number(form.quantity), unit: selected.unit, harvestDate: form.date, price: Number(form.price), condition: form.condition, createdAt: new Date().toISOString(), farmer: selected.farmer }); setPreview(false); };
  return <section className="lab-card forward-card"><div className="lab-card-head"><div><div className="eyebrow">Harvest Forward Contract · prototype</div><h3>Plan future commerce against verified evidence</h3><p>Create a proposed agreement from a verified harvest. This is a forward-commerce concept, not a financial instrument or deployed smart contract.</p></div><WalletCards size={21} /></div><div className="prototype-label"><ShieldCheck size={14} /> Prototype — Forward Commerce Concept</div>{loading ? <div className="lab-loading"><Sparkles size={15} /> Loading verified harvests and Passport history…</div> : error ? <div className="lab-error"><CircleAlert size={15} />{error}</div> : !harvests.length ? <div className="lab-loading">No verified harvests are available for a forward-contract proposal.</div> : <><div className="forward-source"><div><span>Verified farmer</span><strong>{passport?.farmer?.name || selected?.farmer}</strong></div><div><span>Verified harvest history</span><strong>{passport?.verified_harvests ?? '—'} harvests · {passport?.completed_sales ?? '—'} sales</strong></div><div><span>Evidence status</span><strong><ShieldCheck size={13} /> Existing CropCred records</strong></div></div><div className="lab-controls"><label>Verified harvest<select value={selectedId} onChange={(e) => chooseHarvest(e.target.value)}>{harvests.map((item) => <option key={item.id} value={item.id}>{item.crop} · {item.quantity} {item.unit} · {item.id}</option>)}</select></label></div>{selected && <div className="forward-harvest-card"><div><div className="eyebrow">Selected verified harvest</div><h4>{selected.crop}</h4><span>{selected.id} · {selected.quantity} {selected.unit} · harvested {selected.date}</span></div><span className="status-badge verified"><span className="status-dot" />VERIFIED</span></div>}<form className="forward-form" onSubmit={createContract}><label>Expected quantity<input type="number" min="1" required value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></label><label>Expected harvest date<input type="date" required value={form.date.includes(' ') ? '' : form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></label><label>Proposed price (INR / {selected?.unit || 'unit'})<input type="number" min="0" step="0.01" required value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="35" /></label><label>Settlement condition<select value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })}><option>After verified delivery confirmation</option><option>After buyer acceptance and verified payment</option><option>After evidence review by CropCred operator</option></select></label><button className="button primary" type="submit">Create proposed contract <ArrowUpRight size={14} /></button></form>{contract && <div className="contract-result"><div className="contract-result-top"><div><div className="eyebrow">Proposed contract</div><h4>{contract.id}</h4></div><span className="status-badge pending"><span className="status-dot" />CREATED</span></div><div className="contract-grid"><div><span>Crop / quantity</span><strong>{contract.crop} · {contract.quantity} {contract.unit}</strong></div><div><span>Proposed price</span><strong>₹{contract.price.toLocaleString('en-IN')} / {contract.unit}</strong></div><div><span>Contract hash</span><strong className="proof-hash">{contract.hash}</strong></div><div><span>Settlement condition</span><strong>{contract.condition}</strong></div></div><div className="forward-timeline">{['Created', 'Verified', 'Harvested', 'Settled'].map((step, index) => <div key={step} className={`forward-step ${index === 0 || (preview && index === 1) ? 'active' : ''}`}><span>{index === 0 || (preview && index === 1) ? <Check size={12} /> : index + 1}</span><strong>{step}</strong>{index < 3 && <i />}</div>)}</div><div className="evidence-requirements"><strong>Evidence required for settlement</strong><span><Check size={12} /> Harvest record and expected quantity</span><span><Check size={12} /> Buyer acceptance or marketplace order</span><span><Check size={12} /> Delivery confirmation and verified payment where applicable</span></div><button className="button outline" onClick={() => setPreview(true)} disabled={preview}>{preview ? 'Settlement preview active' : 'Preview simulated settlement'}</button>{preview && <div className="settlement-preview"><Sparkles size={15} /><div><strong>Simulated preview only</strong><span>Prototype state: evidence would be reviewed before settlement. No funds moved, token was minted, or blockchain transaction was created.</span></div></div>}</div>}</>}</section>;
}

export default function HackathonLab({ onOrderCreated }: { onOrderCreated: (listing: Listing, quantity?: number) => Promise<void> }) {
  const [showRoadmap, setShowRoadmap] = useState(true);
  return <AppShell title="Innovation Lab" subtitle="Phase 2 · Safe presentation mode"><PageFrame><div className="page-intro"><div><div className="eyebrow">Innovation Lab · Phase 3</div><h2>Prototype future commerce with evidence.</h2><p>Explore private proof, human-approved commerce intents, and forward-contract concepts without moving funds.</p></div><span className="verified-chip"><ShieldCheck size={13} /> Prototype</span></div><div className="lab-banner"><ShieldCheck size={18} /><div><strong>Privacy-first, local verification</strong><span>Only verified aggregate records are used. Individual buyers, prices, dates, wallets, and transactions never appear in the proof result.</span></div></div><div className="lab-grid"><ZKCreditDashboard /><AutonomousAgentPanel onOrderCreated={onOrderCreated} />{showRoadmap && <HarvestFuturesLaunchpad />}</div><div className="lab-toggle"><button className="button outline" onClick={() => setShowRoadmap(!showRoadmap)}>{showRoadmap ? 'Focus on Private Economic Proof' : 'Show other roadmap concepts'}</button></div><div className="info-strip"><div className="info-strip-icon"><ShieldCheck size={18} /></div><div><strong>Existing Solana functionality is unchanged.</strong><span>Real payments continue to use explicit wallet approval, Solana Devnet confirmation, exact lamport checks, and backend-independent verification.</span></div></div></PageFrame></AppShell>;
}
