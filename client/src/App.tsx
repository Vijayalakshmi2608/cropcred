import { Redirect, Route, Switch } from 'wouter';
import { useEffect, useState } from 'react';
import { Dashboard, B2B, HarvestDetail, Harvests, Marketplace, MarketplaceDetail, NewHarvest, NotFound, Orders, PassportPage, Profile } from './pages/Workspace';
import { listings, type Harvest, type Listing, type Order, orders as seedOrders, harvests as seedHarvests } from './data/mockData';
import { createHarvest, createOrder, getHarvests, getOrders } from './services/api';

export default function App() {
  const [harvests, setHarvests] = useState<Harvest[]>(seedHarvests);
  const [orders, setOrders] = useState<Order[]>(seedOrders);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([getHarvests(), getOrders()]).then(([nextHarvests, nextOrders]) => {
      if (active) { setHarvests(nextHarvests); setOrders(nextOrders); setLoading(false); }
    }).catch(() => setLoading(false));
    return () => { active = false; };
  }, []);

  const addHarvest = async (harvest: Harvest) => {
    try { const created = await createHarvest({ crop: harvest.crop, quantity: harvest.quantity, unit: harvest.unit, harvest_date: harvest.date, expected_price: Number(harvest.price.replace(/[^0-9.]/g, '')), location: harvest.location, description: harvest.description, farmer_id: 'farmer-01' }); setHarvests((current) => [created, ...current]); }
    catch { setHarvests((current) => [harvest, ...current]); }
  };
  const addOrder = async (listing: Listing) => {
    try { const created = await createOrder(listing.listingId, Math.min(10, listing.available)); setOrders((current) => [created, ...current]); }
    catch { setOrders((current) => [{ id: `CR-ORD-${String(232 + current.length).padStart(5, '0')}`, crop: listing.crop, quantity: `10 ${listing.unit}`, amount: listing.price.replace(/\/.*$/, ''), buyer: 'CropCred marketplace preorder', status: 'ORDER PLACED', date: '22 Sep 2026', wallet: 'Awaiting Solana transaction' }, ...current]); }
  };
  const props = { harvests, setHarvests, orders, setOrders };
  return <Switch><Route path="/"><Redirect to="/dashboard" /></Route><Route path="/dashboard"><Dashboard {...props} /></Route><Route path="/harvests/new"><NewHarvest onRegistered={addHarvest} /></Route><Route path="/harvests/:id"><HarvestDetail {...props} /></Route><Route path="/harvests"><Harvests {...props} /></Route><Route path="/marketplace/:id"><MarketplaceDetail onPreorder={addOrder} /></Route><Route path="/marketplace"><Marketplace onPreorder={addOrder} /></Route><Route path="/b2b"><B2B /></Route><Route path="/orders"><Orders {...props} /></Route><Route path="/passport"><PassportPage /></Route><Route path="/profile"><Profile /></Route><Route><NotFound /></Route></Switch>;
}
