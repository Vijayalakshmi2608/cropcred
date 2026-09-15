export type Farmer = {
  id: string;
  name: string;
  location: string;
  crops: string[];
  farmSize: string;
  initials: string;
};

export type Harvest = {
  id: string;
  crop: string;
  quantity: number;
  unit: string;
  date: string;
  price: string;
  status: 'VERIFIED' | 'PENDING' | 'REGISTERED';
  location: string;
  farmer: string;
  description?: string;
};

export type Listing = Harvest & {
  listingId: string;
  available: number;
  verification: string;
};

export type Demand = {
  id: string;
  buyerType: 'RESTAURANT' | 'RETAILER' | 'PROCESSOR';
  buyer: string;
  crop: string;
  quantity: string;
  price: string;
  location: string;
  due: string;
  dueTone: 'urgent' | 'calm';
};

export type Order = {
  id: string;
  crop: string;
  quantity: string;
  amount: string;
  buyer: string;
  status: 'ORDER PLACED' | 'PAYMENT VERIFIED' | 'DELIVERY CONFIRMED' | 'COMPLETED';
  date: string;
  wallet: string;
};

export const currentFarmer: Farmer = {
  id: 'farmer-01',
  name: 'Arun Kumar',
  location: 'Kanchipuram, Tamil Nadu',
  crops: ['Tomatoes', 'Bananas', 'Coconut'],
  farmSize: '4.2 acres',
  initials: 'AK',
};

export const farmers: Farmer[] = [
  currentFarmer,
  { id: 'farmer-02', name: 'Meena Reddy', location: 'Chittoor, Andhra Pradesh', crops: ['Bananas', 'Mango'], farmSize: '6.8 acres', initials: 'MR' },
  { id: 'farmer-03', name: 'Ravi Singh', location: 'Nashik, Maharashtra', crops: ['Onion', 'Grapes'], farmSize: '3.1 acres', initials: 'RS' },
];

export const harvests: Harvest[] = [
  { id: 'CR-HRV-00041', crop: 'Tomatoes', quantity: 500, unit: 'kg', date: '18 Sep 2026', price: '₹35/kg', status: 'VERIFIED', location: 'Kanchipuram, Tamil Nadu', farmer: 'Arun Kumar', description: 'Open-field tomatoes, graded A. Ready for verified commerce.' },
  { id: 'CR-HRV-00042', crop: 'Bananas', quantity: 300, unit: 'kg', date: '20 Sep 2026', price: '₹42/kg', status: 'PENDING', location: 'Kanchipuram, Tamil Nadu', farmer: 'Arun Kumar', description: 'Robusta bananas, harvested at commercial maturity.' },
  { id: 'CR-HRV-00039', crop: 'Coconut', quantity: 180, unit: 'units', date: '11 Sep 2026', price: '₹28/unit', status: 'VERIFIED', location: 'Kanchipuram, Tamil Nadu', farmer: 'Arun Kumar' },
  { id: 'CR-HRV-00037', crop: 'Tomatoes', quantity: 420, unit: 'kg', date: '05 Sep 2026', price: '₹32/kg', status: 'VERIFIED', location: 'Chittoor, Andhra Pradesh', farmer: 'Meena Reddy' },
  { id: 'CR-HRV-00036', crop: 'Mango', quantity: 650, unit: 'kg', date: '02 Sep 2026', price: '₹58/kg', status: 'VERIFIED', location: 'Chittoor, Andhra Pradesh', farmer: 'Meena Reddy' },
  { id: 'CR-HRV-00035', crop: 'Grapes', quantity: 240, unit: 'kg', date: '28 Aug 2026', price: '₹74/kg', status: 'PENDING', location: 'Nashik, Maharashtra', farmer: 'Ravi Singh' },
];

export const listings: Listing[] = [
  ...harvests.filter((h) => h.status === 'VERIFIED').map((h, index) => ({ ...h, listingId: `listing-${index + 1}`, available: h.quantity, verification: 'Verified harvest' })),
  { id: 'CR-HRV-00029', listingId: 'listing-07', crop: 'Onion', quantity: 800, unit: 'kg', date: '24 Aug 2026', price: '₹26/kg', status: 'VERIFIED', location: 'Nashik, Maharashtra', farmer: 'Ravi Singh', available: 800, verification: 'Verified harvest' },
  { id: 'CR-HRV-00028', listingId: 'listing-08', crop: 'Mango', quantity: 420, unit: 'kg', date: '22 Aug 2026', price: '₹62/kg', status: 'VERIFIED', location: 'Chittoor, Andhra Pradesh', farmer: 'Meena Reddy', available: 420, verification: 'Verified harvest' },
];

export const demands: Demand[] = [
  { id: 'DEM-1001', buyerType: 'RESTAURANT', buyer: 'Chennai Restaurant Collective', crop: 'Tomatoes', quantity: '500 kg / week', price: '₹32–₹38/kg', location: 'Chennai', due: '3 days remaining', dueTone: 'urgent' },
  { id: 'DEM-1002', buyerType: 'RETAILER', buyer: 'Southstar Grocers', crop: 'Bananas', quantity: '1,000 kg', price: '₹38–₹44/kg', location: 'Bengaluru', due: 'Weekly requirement', dueTone: 'calm' },
  { id: 'DEM-1003', buyerType: 'PROCESSOR', buyer: 'Harvest Kitchen Co.', crop: 'Tomatoes', quantity: '2,000 kg / month', price: '₹29–₹34/kg', location: 'Coimbatore', due: '8 days remaining', dueTone: 'calm' },
  { id: 'DEM-1004', buyerType: 'RESTAURANT', buyer: 'The Green Table', crop: 'Coconut', quantity: '300 units / week', price: '₹25–₹30/unit', location: 'Pondicherry', due: '5 days remaining', dueTone: 'calm' },
  { id: 'DEM-1005', buyerType: 'RETAILER', buyer: 'Daily Basket', crop: 'Onion', quantity: '750 kg', price: '₹24–₹28/kg', location: 'Chennai', due: '12 days remaining', dueTone: 'calm' },
];

export const orders: Order[] = [
  { id: 'CR-ORD-00231', crop: 'Tomatoes', quantity: '10 kg', amount: '₹350', buyer: 'Chennai Restaurant', status: 'COMPLETED', date: '21 Sep 2026', wallet: 'Awaiting Solana transaction' },
  { id: 'CR-ORD-00229', crop: 'Coconut', quantity: '40 units', amount: '₹1,120', buyer: 'The Green Table', status: 'DELIVERY CONFIRMED', date: '20 Sep 2026', wallet: 'Awaiting Solana transaction' },
  { id: 'CR-ORD-00224', crop: 'Tomatoes', quantity: '60 kg', amount: '₹2,100', buyer: 'Harvest Kitchen Co.', status: 'PAYMENT VERIFIED', date: '18 Sep 2026', wallet: 'Awaiting Solana transaction' },
  { id: 'CR-ORD-00219', crop: 'Bananas', quantity: '120 kg', amount: '₹5,040', buyer: 'Southstar Grocers', status: 'ORDER PLACED', date: '16 Sep 2026', wallet: 'Awaiting Solana transaction' },
  { id: 'CR-ORD-00213', crop: 'Mango', quantity: '80 kg', amount: '₹4,640', buyer: 'Daily Basket', status: 'COMPLETED', date: '12 Sep 2026', wallet: 'Awaiting Solana transaction' },
  { id: 'CR-ORD-00208', crop: 'Tomatoes', quantity: '25 kg', amount: '₹875', buyer: 'Chennai Restaurant', status: 'COMPLETED', date: '09 Sep 2026', wallet: 'Awaiting Solana transaction' },
];

export const passport = {
  verifiedHarvests: 12,
  completedSales: 86,
  fulfillment: '94%',
  tradeValue: '₹2.4L',
  lastUpdated: '21 Sep 2026, 14:32 IST',
};

export const activity = [
  { label: 'Harvest Registered', detail: '500 kg Tomatoes', date: '18 Sep 2026', icon: 'harvest', tone: 'copper' },
  { label: 'Order Completed', detail: '10 kg Tomatoes · ₹350', date: '20 Sep 2026', icon: 'order', tone: 'mint' },
  { label: 'Payment Verified', detail: 'Evidence recorded locally', date: '20 Sep 2026', icon: 'payment', tone: 'violet' },
  { label: 'Delivery Confirmed', detail: 'Order #CR-ORD-00231', date: '21 Sep 2026', icon: 'delivery', tone: 'blue' },
];
