import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, MapPin, Plus, ShieldCheck, X } from 'lucide-react';
import { Link, useLocation, useRoute } from 'wouter';
import { AppShell, EmptyState, PageFrame, SectionHeading } from '../components/cropcred';
import { awardAuctionOffer, createAuction, getAuction, getAuctionOffers, getAuctions, submitAuctionOffer } from '../services/api';

type Auction = {
  id: string;
  buyer_name: string;
  buyer_type: string;
  crop: string;
  crop_batch_id?: string | null;
  quantity: number;
  unit: string;
  price_min: number;
  price_max: number;
  price_range_label?: string;
  deadline: string;
  delivery_location: string;
  quality_requirements?: string;
  evidence_requirements?: string;
  status: string;
  offer_count?: number;
  created_at?: string;
};

function formatCurrency(value: number) {
  return `₹${Number(value).toLocaleString('en-IN')}`;
}

function dateLabel(value?: string) {
  if (!value) return 'N/A';
  const date = new Date(value.includes('T') ? value : `${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function AuctionCard({ auction }: { auction: Auction }) {
  return <article className="demand-network-card"><div className="demand-card-top"><span className="eyebrow">{auction.id} · {auction.buyer_type}</span><span className={`demand-status ${String(auction.status).toLowerCase()}`}>{auction.status}</span></div><h3>{auction.crop}</h3><div className="demand-card-grid"><div><span>Required</span><strong>{auction.quantity} {auction.unit}</strong></div><div><span>Price range</span><strong>{formatCurrency(auction.price_min)}–{formatCurrency(auction.price_max)}/{auction.unit}</strong></div><div><span>Deadline</span><strong>{dateLabel(auction.deadline)}</strong></div><div><span>Location</span><strong>{auction.delivery_location}</strong></div></div><div className="demand-buyer"><span className="buyer-check"><Check size={13} /></span><span><strong>{auction.buyer_name}</strong><small><MapPin size={11} /> {auction.delivery_location} · Verified buyer</small></span></div><div className="demand-card-actions"><Link href={`/auctions/${auction.id}`} className="button primary">View auction</Link>{auction.offer_count ? <Link href={`/auctions/${auction.id}`} className="text-link">{auction.offer_count} offer{auction.offer_count === 1 ? '' : 's'} <ArrowRight size={13} /></Link> : <span className="text-link">Awaiting offers</span>}</div></article>;
}

export function AuctionNetwork() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({
    buyer_name: 'Green Valley Foods',
    buyer_type: 'RESTAURANT',
    crop: 'Tomatoes',
    quantity: '250',
    unit: 'kg',
    price_min: '30',
    price_max: '42',
    deadline: '2026-10-05',
    delivery_location: 'Coimbatore',
    quality_requirements: 'Grade A + traceability',
    evidence_requirements: 'Photo + lot record'
  });
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const next = await getAuctions();
      setAuctions(next);
    } catch {
      setAuctions([]);
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    try {
      setError('');
      await createAuction({
        ...form,
        quantity: Number(form.quantity),
        price_min: Number(form.price_min),
        price_max: Number(form.price_max),
      });
      setMessage('Auction opened. Farmers can now submit offers.');
      setCreateOpen(false);
      load();
    } catch (reason: any) {
      setError(reason.message || 'Auction could not be created.');
    }
  };

  return <AppShell title="Crop Auction Network" subtitle="Buyer-led procurement with manual offer selection and existing order flow"><PageFrame><div className="network-hero"><div><div className="eyebrow light">Open-market procurement</div><h2>Buyer posts demand.<br /><em>Farmers respond.</em></h2><p>CropCred keeps the auction human-led: the buyer reviews offers, compares trade-offs, and selects the winning farmer before reusing the existing Solana Devnet payment and delivery flow.</p></div><div className="network-flow"><span>BUYER</span><ArrowRight /><span>AUCTION</span><ArrowRight /><span>FARMS</span><ArrowRight /><strong>ORDER</strong></div></div>{message && <div className="network-message"><Check size={15} /> {message}<button onClick={() => setMessage('')}><X size={14} /></button></div>}{error && <div className="form-error"><X size={15} /> {error}</div>}<div className="demand-toolbar"><div><div className="eyebrow">Buyer and farmer workflow</div><h2>Open auctions</h2><p>All auctions remain optional and use the same order, payment, and evidence pathways as the rest of CropCred.</p></div><button className="button primary" onClick={() => setCreateOpen(true)}><Plus size={15} /> Create auction</button></div>{createOpen && <div className="modal-backdrop"><div className="payment-modal demand-modal"><button className="modal-close" onClick={() => setCreateOpen(false)}><X size={16} /></button><div className="eyebrow">Buyer auction</div><h3>Create crop auction</h3><div className="form-grid"><label>Buyer<input value={form.buyer_name} onChange={(event) => setForm({ ...form, buyer_name: event.target.value })} /></label><label>Buyer type<select value={form.buyer_type} onChange={(event) => setForm({ ...form, buyer_type: event.target.value })}><option value="RESTAURANT">RESTAURANT</option><option value="RETAILER">RETAILER</option><option value="PROCESSOR">PROCESSOR</option><option value="INSTITUTION">INSTITUTION</option></select></label><label>Crop<input value={form.crop} onChange={(event) => setForm({ ...form, crop: event.target.value })} /></label><label>Quantity<input type="number" min="1" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} /></label><label>Unit<select value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })}><option>kg</option><option>units</option><option>crates</option></select></label><label>Price min<input type="number" min="0" value={form.price_min} onChange={(event) => setForm({ ...form, price_min: event.target.value })} /></label><label>Price max<input type="number" min="0" value={form.price_max} onChange={(event) => setForm({ ...form, price_max: event.target.value })} /></label><label>Deadline<input type="date" value={form.deadline} onChange={(event) => setForm({ ...form, deadline: event.target.value })} /></label><label>Delivery location<input value={form.delivery_location} onChange={(event) => setForm({ ...form, delivery_location: event.target.value })} /></label><label>Quality requirements<textarea value={form.quality_requirements} onChange={(event) => setForm({ ...form, quality_requirements: event.target.value })} /></label><label>Evidence requirements<textarea value={form.evidence_requirements} onChange={(event) => setForm({ ...form, evidence_requirements: event.target.value })} /></label></div><button className="button primary payment-action" onClick={submit}>Open auction</button></div></div>}<div className="demand-grid">{auctions.length ? auctions.map((auction) => <AuctionCard key={auction.id} auction={auction} />) : <div className="demand-grid" style={{ gridTemplateColumns: '1fr' }}><EmptyState title="No auctions yet" description="Post a buyer requirement to start a manual auction flow." action={<button className="button primary" onClick={() => setCreateOpen(true)}>Create first auction</button>} /></div>}</div></PageFrame></AppShell>;
}

export function AuctionDetailPage() {
  const [, params] = useRoute('/auctions/:id');
  const [, navigate] = useLocation();
  const [auction, setAuction] = useState<Auction | null>(null);
  const [offers, setOffers] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({
    farmerId: 'farmer-01',
    quantity: '200',
    offeredPrice: '36',
    deliveryEstimate: '3 days',
    message: 'Ready for dispatch'
  });

  const load = async () => {
    if (!params?.id) return;
    const nextAuction = await getAuction(params.id).catch(() => null);
    setAuction(nextAuction);
    if (nextAuction) {
      const nextOffers = await getAuctionOffers(nextAuction.id).catch(() => []);
      setOffers(nextOffers);
    }
  };

  useEffect(() => { load(); }, [params?.id]);

  const submitOffer = async () => {
    if (!auction) return;
    try {
      await submitAuctionOffer(auction.id, {
        farmer_id: form.farmerId,
        quantity: Number(form.quantity),
        offered_price: Number(form.offeredPrice),
        delivery_estimate: form.deliveryEstimate,
        message: form.message,
      });
      setMessage('Offer submitted successfully. Buyer can review and decide.');
      load();
    } catch (reason: any) {
      setMessage(reason.message || 'Unable to submit the offer.');
    }
  };

  const awardOffer = async (offerId: string) => {
    if (!auction) return;
    try {
      const result = await awardAuctionOffer(auction.id, offerId);
      setMessage(`Offer accepted. Order ${result.order.id} created and moved into the existing payment flow.`);
      load();
    } catch (reason: any) {
      setMessage(reason.message || 'Unable to award this offer.');
    }
  };

  if (!auction) {
    return <AppShell title="Auction" subtitle="Loading"><PageFrame><div className="passport-loading">Loading auction…</div></PageFrame></AppShell>;
  }

  return <AppShell title="Auction detail" subtitle={auction.id}><PageFrame className="narrow-page"><button className="back-link" onClick={() => navigate('/auctions')}><ArrowLeft size={15} /> Back to auctions</button>{message && <div className="network-message"><Check size={15} /> {message}<button onClick={() => setMessage('')}><X size={14} /></button></div>}<div className="detail-hero"><div><div className="eyebrow">Buyer auction</div><h2>{auction.crop}</h2><p>{auction.buyer_name} · {auction.buyer_type}</p></div><span className={`demand-status ${String(auction.status).toLowerCase()}`}>{auction.status}</span></div><div className="detail-metrics"><div><span>Required</span><strong>{auction.quantity} {auction.unit}</strong></div><div><span>Price range</span><strong>{formatCurrency(auction.price_min)}–{formatCurrency(auction.price_max)}/{auction.unit}</strong></div><div><span>Deadline</span><strong>{dateLabel(auction.deadline)}</strong></div><div><span>Delivery</span><strong>{auction.delivery_location}</strong></div></div><div className="demand-grid" style={{ gridTemplateColumns: '1fr 1fr' }}><section className="detail-card"><SectionHeading eyebrow="Requirements" title="Auction criteria" description="The buyer defines the minimum quality and evidence expectations." /><div className="batch-record-list"><div><span>Crop batch</span><strong>{auction.crop_batch_id || 'Not tied to a batch'}</strong></div><div><span>Quality</span><strong>{auction.quality_requirements || 'No specific quality note'}</strong></div><div><span>Evidence</span><strong>{auction.evidence_requirements || 'No extra evidence required'}</strong></div><div><span>Buyer</span><strong>{auction.buyer_name}</strong></div></div>{auction.crop_batch_id && <Link href={`/crop-batches/${auction.crop_batch_id}`} className="text-link">View crop batch <ArrowRight size={13} /></Link>}<Link href="/passport" className="text-link">View farmer passport <ArrowRight size={13} /></Link></section><section className="detail-card"><SectionHeading eyebrow="Farmer response" title="Submit offer" description="Farmers can compare the buyer requirement and send a tailored quote." /><div className="form-grid"><label>Farmer ID<input value={form.farmerId} onChange={(event) => setForm({ ...form, farmerId: event.target.value })} /></label><label>Quantity<input type="number" min="1" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} /></label><label>Offered price<input type="number" min="0" value={form.offeredPrice} onChange={(event) => setForm({ ...form, offeredPrice: event.target.value })} /></label><label>Delivery estimate<input value={form.deliveryEstimate} onChange={(event) => setForm({ ...form, deliveryEstimate: event.target.value })} /></label><label>Message<textarea value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} /></label></div><button className="button primary payment-action" onClick={submitOffer}>Submit offer</button></section></div><section className="detail-card"><SectionHeading eyebrow="Offer review" title="Farmer offers" description="The buyer reviews each response and manually chooses the best fit. No automatic ranking is applied." /><div className="response-list">{offers.length ? offers.map((offer) => <div className="response-card" key={offer.id}><div><strong>{offer.farmer_name || offer.farmer_id}</strong><span>{offer.quantity} {auction.unit} · {formatCurrency(offer.offered_price)}/{auction.unit}</span><small>{offer.delivery_estimate} · {offer.message || 'No message'}</small></div><div className="response-actions"><span className="match-fit"><ShieldCheck size={13} /> {offer.status}</span>{offer.status === 'SUBMITTED' && <button className="button primary" onClick={() => awardOffer(offer.id)}>Accept offer</button>}</div></div>) : <EmptyState title="No offers yet" description="Farmers will appear here once they submit a suitable price and delivery plan." />}</div></section></PageFrame></AppShell>;
}
