import { Redirect, Route, Switch } from 'wouter';
import { useState } from 'react';
import { Dashboard, B2B, HarvestDetail, Harvests, Marketplace, MarketplaceDetail, NewHarvest, NotFound, Orders, PassportPage, Profile } from './pages/Workspace';
import { listings, type Harvest, type Listing, type Order, orders as seedOrders, harvests as seedHarvests } from './data/mockData';

export default function App() {
  const [harvests, setHarvests] = useState<Harvest[]>(seedHarvests);
  const [orders, setOrders] = useState<Order[]>(seedOrders);
  const addHarvest = (harvest: Harvest) => setHarvests((current) => [harvest, ...current]);
  const addOrder = (listing: Listing) => setOrders((current) => [{ id: `CR-ORD-${String(232 + current.length).padStart(5, '0')}`, crop: listing.crop, quantity: `10 ${listing.unit}`, amount: listing.price.replace(/\/.*$/, ''), buyer: 'CropCred marketplace preorder', status: 'ORDER PLACED', date: '22 Sep 2026', wallet: 'Awaiting Solana transaction' }, ...current]);
  const props = { harvests, setHarvests, orders, setOrders };
  return <Switch><Route path="/"><Redirect to="/dashboard" /></Route><Route path="/dashboard"><Dashboard {...props} /></Route><Route path="/harvests/new"><NewHarvest onRegistered={addHarvest} /></Route><Route path="/harvests/:id"><HarvestDetail {...props} /></Route><Route path="/harvests"><Harvests {...props} /></Route><Route path="/marketplace/:id"><MarketplaceDetail onPreorder={addOrder} /></Route><Route path="/marketplace"><Marketplace onPreorder={addOrder} /></Route><Route path="/b2b"><B2B /></Route><Route path="/orders"><Orders {...props} /></Route><Route path="/passport"><PassportPage /></Route><Route path="/profile"><Profile /></Route><Route><NotFound /></Route></Switch>;
}
