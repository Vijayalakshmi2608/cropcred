import { Redirect, Route, Switch } from 'wouter';
import { useEffect, useState } from 'react';
import { Dashboard, B2B, HarvestDetail, Harvests, Marketplace, MarketplaceDetail, NewHarvest, NotFound, Orders, Profile, VerifyCredential } from './pages/Workspace';
import PassportIntelligence from './pages/PassportIntelligence';
import PublicCredential from './pages/PublicCredential';
import DemandNetwork from './pages/DemandNetwork';
import { AuctionDetailPage, AuctionNetwork } from './pages/Auctions';
import Insights from './pages/Insights';
import Landing from './pages/Landing';
import { CropBatches, CropBatchDetail, NewCropBatch } from './pages/CropBatches';
import { listings, type Harvest, type Listing, type Order, orders as seedOrders, harvests as seedHarvests } from './data/mockData';
import { createHarvest, createOrder, getHarvests, getOrders, CROP_CRED_API_BASE } from './services/api';

export default function App() {
  const [harvests, setHarvests] = useState<Harvest[]>(seedHarvests);
  const [orders, setOrders] = useState<Order[]>(seedOrders);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([getHarvests(), getOrders()]).then(([nextHarvests, nextOrders]) => {
      if (active) { setHarvests(nextHarvests); setOrders(nextOrders); setLoading(false); }
    }).catch((error) => { if (active) { setApiError(error instanceof Error ? error.message : 'CropCred API could not be reached.'); setLoading(false); } });
    return () => { active = false; };
  }, []);

  const addHarvest = async (harvest: Harvest) => {
    try { const created = await createHarvest({ crop: harvest.crop, quantity: harvest.quantity, unit: harvest.unit, harvest_date: harvest.date, expected_price: Number(harvest.price.replace(/[^0-9.]/g, '')), location: harvest.location, description: harvest.description, farmer_id: 'farmer-01' }); setHarvests((current) => [created, ...current]); }
    catch (error) { setApiError(error instanceof Error ? error.message : 'Harvest could not be saved.'); }
  };
  const addOrder = async (listing: Listing) => {
    try { const created = await createOrder(listing.listingId, Math.min(10, listing.available)); setOrders((current) => [created, ...current]); }
    catch (error) { setApiError(error instanceof Error ? error.message : 'Order could not be created.'); }
  };
  const props = { harvests, setHarvests, orders, setOrders };
  return <><div className="api-connection-banner" role="status"><span className={`api-dot ${apiError ? 'error' : 'ok'}`} />{apiError ? <><strong>Live API unavailable.</strong><span>{apiError} Configure <code>VITE_API_BASE_URL</code> for this deployment.</span></> : <><strong>Live data connection</strong><span>{CROP_CRED_API_BASE}</span></>}</div><Switch><Route path="/"><Landing /></Route><Route path="/dashboard"><Dashboard {...props} /></Route><Route path="/harvests/new"><NewHarvest onRegistered={addHarvest} /></Route><Route path="/harvests/:id"><HarvestDetail {...props} /></Route><Route path="/harvests"><Harvests {...props} /></Route><Route path="/crop-batches/new"><NewCropBatch harvests={harvests} /></Route><Route path="/crop-batches/:id"><CropBatchDetail /></Route><Route path="/crop-batches"><CropBatches /></Route><Route path="/marketplace/:id"><MarketplaceDetail onPreorder={addOrder} /></Route><Route path="/marketplace"><Marketplace onPreorder={addOrder} /></Route><Route path="/b2b"><DemandNetwork /></Route><Route path="/auctions/:id"><AuctionDetailPage /></Route><Route path="/auctions"><AuctionNetwork /></Route><Route path="/orders"><Orders {...props} /></Route><Route path="/passport"><PassportIntelligence /></Route><Route path="/insights"><Insights /></Route><Route path="/profile"><Profile orders={orders} /></Route><Route path="/verify/:credentialId"><PublicCredential /></Route><Route><NotFound /></Route></Switch></>;
}
