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
import HackathonLab from './pages/HackathonLab';
import { listings, type Harvest, type Listing, type Order } from './data/mockData';
import { harvests as demoHarvests, orders as demoOrders } from './data/mockData';
import { createHarvest, createOrder, getHarvests, getOrders } from './services/api';

export default function App() {
  const [harvests, setHarvests] = useState<Harvest[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [offlineDemo, setOfflineDemo] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([getHarvests(), getOrders()]).then(([nextHarvests, nextOrders]) => {
      if (active) { setHarvests(nextHarvests); setOrders(nextOrders); setLoading(false); }
    }).catch(() => { if (active) { setHarvests(demoHarvests); setOrders(demoOrders); setOfflineDemo(true); setLoading(false); } });
    return () => { active = false; };
  }, []);

  const addHarvest = async (harvest: Harvest) => {
    try { const created = await createHarvest({ crop: harvest.crop, quantity: harvest.quantity, unit: harvest.unit, harvest_date: harvest.date, expected_price: Number(harvest.price.replace(/[^0-9.]/g, '')), location: harvest.location, description: harvest.description, farmer_id: 'farmer-01' }); setHarvests((current) => [created, ...current]); }
    catch { setOfflineDemo(true); }
  };
  const addOrder = async (listing: Listing, requestedQuantity = Math.min(10, listing.available)) => {
    try { const created = await createOrder(listing.listingId, Math.max(1, Math.min(requestedQuantity, listing.available))); setOrders((current) => [created, ...current]); }
    catch { setOfflineDemo(true); }
  };
  const props = { harvests, setHarvests, orders, setOrders };
  return <Switch><Route path="/"><Landing /></Route><Route path="/dashboard"><Dashboard {...props} /></Route><Route path="/lab"><HackathonLab onOrderCreated={addOrder} /></Route><Route path="/harvests/new"><NewHarvest onRegistered={addHarvest} /></Route><Route path="/harvests/:id"><HarvestDetail {...props} /></Route><Route path="/harvests"><Harvests {...props} /></Route><Route path="/crop-batches/new"><NewCropBatch harvests={harvests} /></Route><Route path="/crop-batches/:id"><CropBatchDetail /></Route><Route path="/crop-batches"><CropBatches /></Route><Route path="/marketplace/:id"><MarketplaceDetail onPreorder={addOrder} /></Route><Route path="/marketplace"><Marketplace onPreorder={addOrder} /></Route><Route path="/b2b"><DemandNetwork /></Route><Route path="/auctions/:id"><AuctionDetailPage /></Route><Route path="/auctions"><AuctionNetwork /></Route><Route path="/orders"><Orders {...props} /></Route><Route path="/passport"><PassportIntelligence /></Route><Route path="/insights"><Insights /></Route><Route path="/profile"><Profile orders={orders} /></Route><Route path="/verify/:credentialId"><PublicCredential /></Route><Route><NotFound /></Route></Switch>;
}
