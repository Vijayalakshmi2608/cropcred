import { demands as demoDemands, listings as demoListings, orders as demoOrders, harvests as demoHarvests, passport as demoPassport, currentFarmer } from '../data/mockData';
import type { Demand, Harvest, Listing, Order } from '../data/mockData';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';
const FALLBACK_DELAY = 180;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  const body = await response.json();
  if (!response.ok || body.success === false) throw new Error(body.error || 'Request failed');
  return body.data ?? body;
}

const dateLabel = (value: string) => {
  if (!value) return value;
  const date = new Date(value.includes('T') ? value : `${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
};

export function mapHarvest(item: any): Harvest {
  return { id: item.id, crop: item.crop, quantity: Number(item.quantity), unit: item.unit, date: item.harvest_date_label || dateLabel(item.harvest_date), price: item.expected_price_label || `₹${item.expected_price}/${item.unit}`, status: item.status, location: item.location, farmer: item.farmer || currentFarmer.name, description: item.description };
}
export function mapListing(item: any): Listing {
  return { ...mapHarvest({ ...item, expected_price: item.price_per_unit, expected_price_label: item.price_label, harvest_date: item.harvest_date }), listingId: item.id, available: Number(item.available ?? item.quantity_available), verification: item.verification || 'Verified harvest' };
}
export function mapOrder(item: any): Order {
  const statusMap: Record<string, Order['status']> = { PLACED: 'ORDER PLACED', PROCESSING: 'PAYMENT VERIFIED', OUT_FOR_DELIVERY: 'DELIVERY CONFIRMED', DELIVERED: 'DELIVERY CONFIRMED', COMPLETED: 'COMPLETED' };
  return { id: item.id, crop: item.crop || 'Harvest supply', quantity: `${item.quantity} ${item.unit}`, amount: item.amount_label || `₹${item.total_amount}`, buyer: item.buyer_name, status: statusMap[item.status] || 'ORDER PLACED', date: dateLabel(item.created_at || '2026-09-22'), wallet: 'Awaiting Solana transaction' };
}
export function mapDemand(item: any): Demand {
  return { id: item.id, buyerType: item.buyer_type, buyer: item.buyer_name, crop: item.crop, quantity: item.quantity_label || `${item.quantity} ${item.unit}`, price: item.price_label || `₹${item.price_min}–₹${item.price_max}/${item.unit}`, location: item.location, due: item.deadline, dueTone: String(item.deadline).toLowerCase().includes('day') && !String(item.deadline).includes('12') ? 'urgent' : 'calm' };
}

export async function getHarvests(): Promise<Harvest[]> { try { return (await request<any[]>('/harvests')).map(mapHarvest); } catch { await new Promise((resolve) => setTimeout(resolve, FALLBACK_DELAY)); return demoHarvests; } }
export async function createHarvest(data: any): Promise<Harvest> { return mapHarvest(await request<any>('/harvests', { method: 'POST', body: JSON.stringify(data) })); }
export async function getMarketplaceListings(): Promise<Listing[]> { try { return (await request<any[]>('/marketplace')).map(mapListing); } catch { return demoListings; } }
export async function getDemands(): Promise<Demand[]> { try { return (await request<any[]>('/demands')).map(mapDemand); } catch { return demoDemands; } }
export async function getOrders(): Promise<Order[]> { try { return (await request<any[]>('/orders')).map(mapOrder); } catch { return demoOrders; } }
export async function createOrder(listingId: string, quantity: number, buyerName = 'CropCred marketplace preorder'): Promise<Order> { return mapOrder(await request<any>('/orders', { method: 'POST', body: JSON.stringify({ listing_id: listingId, quantity, buyer_name: buyerName, buyer_type: 'RETAILER' }) })); }
export async function updateOrderStatus(id: string, status: string): Promise<Order> { return mapOrder(await request<any>(`/orders/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) })); }
export async function confirmDelivery(id: string): Promise<Order> { return mapOrder(await request<any>(`/deliveries/${id}/confirm`, { method: 'POST' })); }
export async function updateFarmerWallet(farmerId: string, walletAddress: string): Promise<{ wallet_address: string }> { return request<{ wallet_address: string }>(`/farmers/${farmerId}/wallet`, { method: 'PUT', body: JSON.stringify({ wallet_address: walletAddress }) }); }
export async function getPassport(farmerId = 'farmer-01') { try { return await request<any>(`/farmers/${farmerId}/passport`); } catch { return demoPassport; } }
