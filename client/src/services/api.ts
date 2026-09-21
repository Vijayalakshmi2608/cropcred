import { currentFarmer } from '../data/mockData';
import type { Demand, Harvest, Listing, Order } from '../data/mockData';

const configuredApiBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
const PUBLIC_API_BASE = 'https://5001-i8d09a2vc4cizj8qt1jla-c5cd14fd.sg2.manus.computer/api';
const API_BASE = (configuredApiBase || PUBLIC_API_BASE).replace(/\/$/, '');
export const CROP_CRED_API_BASE = API_BASE;
export const CROP_CRED_API_CONFIGURED = Boolean(configuredApiBase || PUBLIC_API_BASE);

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const body = await response.json();
  if (!response.ok || body.success === false) throw new Error(typeof body.error === 'string' ? body.error : body.error?.message || 'Request failed');
  return body.data ?? body;
}

const dateLabel = (value: string) => { if (!value) return value; const date = new Date(value.includes('T') ? value : `${value}T12:00:00`); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); };
export function mapHarvest(item: any): Harvest { return { id: item.id, crop: item.crop, quantity: Number(item.quantity), unit: item.unit, date: item.harvest_date_label || dateLabel(item.harvest_date), price: item.expected_price_label || `₹${item.expected_price}/${item.unit}`, status: item.status, location: item.location, farmer: item.farmer || currentFarmer.name, description: item.description }; }
export function mapListing(item: any): Listing { return { ...mapHarvest({ ...item, expected_price: item.price_per_unit, expected_price_label: item.price_label, harvest_date: item.harvest_date }), listingId: item.id, available: Number(item.available ?? item.quantity_available), verification: item.verification || 'Verified harvest' }; }
export function mapOrder(item: any): Order { const statusMap: Record<string, Order['status']> = { PLACED: 'ORDER PLACED', PENDING_PAYMENT: 'ORDER PLACED', PAYMENT_PROCESSING: 'PAYMENT VERIFIED', PAID: 'PAYMENT VERIFIED', PROCESSING: 'PAYMENT VERIFIED', OUT_FOR_DELIVERY: 'DELIVERY CONFIRMED', DELIVERED: 'DELIVERY CONFIRMED', COMPLETED: 'COMPLETED' }; return { id: item.id, crop: item.crop || 'Harvest supply', quantity: `${item.quantity} ${item.unit}`, amount: item.amount_label || `₹${item.total_amount}`, buyer: item.buyer_name, status: statusMap[item.status] || 'ORDER PLACED', date: dateLabel(item.created_at || '2026-09-22'), wallet: item.transaction_signature ? item.transaction_signature : 'Awaiting Solana transaction' }; }
export function mapDemand(item: any): Demand { return { id: item.id, buyerType: item.buyer_type, buyer: item.buyer_name, crop: item.crop, quantity: item.quantity_label || `${item.quantity} ${item.unit}`, price: item.price_label || `₹${item.price_min}–₹${item.price_max}/${item.unit}`, location: item.location, due: item.deadline, dueTone: String(item.deadline).toLowerCase().includes('day') && !String(item.deadline).includes('12') ? 'urgent' : 'calm' }; }
export async function getHarvests(): Promise<Harvest[]> { return (await request<any[]>('/harvests')).map(mapHarvest); }
export async function createHarvest(data: any): Promise<Harvest> { return mapHarvest(await request<any>('/harvests', { method: 'POST', body: JSON.stringify(data) })); }
export async function getMarketplaceListings(): Promise<Listing[]> { return (await request<any[]>('/marketplace')).map(mapListing); }
export async function getDemands(): Promise<Demand[]> { return (await request<any[]>('/demands')).map(mapDemand); }
export async function getDemandNetwork() { return request<any[]>('/demands'); }
export async function createDemand(data: any) { return request<any>('/demands', { method: 'POST', body: JSON.stringify(data) }); }
export async function getDemandResponses(demandId: string) { return request<any[]>(`/demands/${demandId}/responses`); }
export async function respondToDemand(demandId: string, data: any) { return request<any>(`/demands/${demandId}/respond`, { method: 'POST', body: JSON.stringify(data) }); }
export async function acceptDemandResponse(demandId: string, responseId: string) { return request<any>(`/demands/${demandId}/accept/${responseId}`, { method: 'POST' }); }
export async function getBuyerProfile(buyerId = 'buyer-1001') { return request<any>(`/buyers/${buyerId}/profile`); }
export async function getFarmerOpportunities(farmerId = 'farmer-01') { return request<any[]>(`/farmers/${farmerId}/opportunities`); }
export async function getInsightsOverview() { return request<any>('/insights/overview'); }
export async function getProductFunnel() { return request<any[]>('/insights/product-funnel'); }
export async function getCommerceInsights() { return request<any>('/insights/commerce'); }
export async function getB2BInsights() { return request<any>('/insights/b2b'); }
export async function getCredentialInsights() { return request<any>('/insights/credentials'); }
export async function getValidationInterviews() { return request<any[]>('/validation/interviews'); }
export async function createValidationInterview(data: any) { return request<any>('/validation/interviews', { method: 'POST', body: JSON.stringify(data) }); }
export async function getProductLearnings() { return request<any[]>('/product-learnings'); }
export async function createProductLearning(data: any) { return request<any>('/product-learnings', { method: 'POST', body: JSON.stringify(data) }); }
export async function getPilots() { return request<any[]>('/pilots'); }
export async function createPilot(data: any) { return request<any>('/pilots', { method: 'POST', body: JSON.stringify(data) }); }
export async function getGtmExperiments() { return request<any[]>('/gtm-experiments'); }
export async function createGtmExperiment(data: any) { return request<any>('/gtm-experiments', { method: 'POST', body: JSON.stringify(data) }); }
export async function getFounderNotes() { return request<any[]>('/founder-notes'); }
export async function createFounderNote(data: any) { return request<any>('/founder-notes', { method: 'POST', body: JSON.stringify(data) }); }
export async function getVerificationEvents() { return request<any[]>('/credential-verification-events'); }
export async function createVerificationEvent(data: any) { return request<any>('/credential-verification-events', { method: 'POST', body: JSON.stringify(data) }); }
export async function getOrders(): Promise<Order[]> { return (await request<any[]>('/orders')).map(mapOrder); }
export async function createOrder(listingId: string, quantity: number, buyerName = 'CropCred marketplace preorder'): Promise<Order> { return mapOrder(await request<any>('/orders', { method: 'POST', body: JSON.stringify({ listing_id: listingId, quantity, buyer_name: buyerName, buyer_type: 'RETAILER' }) })); }
export async function updateOrderStatus(id: string, status: string): Promise<Order> { return mapOrder(await request<any>(`/orders/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) })); }
export async function confirmDelivery(id: string): Promise<Order> { return mapOrder(await request<any>(`/deliveries/${id}/confirm`, { method: 'POST' })); }
export async function updateFarmerWallet(farmerId: string, walletAddress: string): Promise<{ wallet_address: string }> { return request<{ wallet_address: string }>(`/farmers/${farmerId}/wallet`, { method: 'PUT', body: JSON.stringify({ wallet_address: walletAddress }) }); }
export async function createPaymentIntent(orderId: string, payerWallet: string) { return request<any>(`/orders/${orderId}/payment-intent`, { method: 'POST', body: JSON.stringify({ payer_wallet: payerWallet }) }); }
export async function verifyPayment(orderId: string, signature: string, payerWallet: string) { return request<any>(`/orders/${orderId}/verify-payment`, { method: 'POST', body: JSON.stringify({ transaction_signature: signature, payer_wallet: payerWallet, network: 'devnet' }) }); }
export async function cancelPayment(orderId: string) { return request<any>(`/orders/${orderId}/cancel-payment`, { method: 'POST' }); }
export async function getPayment(orderId: string) { return request<any>(`/orders/${orderId}/payment`); }
export async function getPassport(farmerId = 'farmer-01') { return request<any>(`/farmers/${farmerId}/passport`); }
export async function getEconomicCredential(farmerId = 'farmer-01') { return request<any>(`/farmers/${farmerId}/economic-credential`); }
export async function getPassportActivity(farmerId = 'farmer-01') { return request<any[]>(`/farmers/${farmerId}/passport/activity`); }
export async function shareCredential(credentialId: string, categories: string[]) { return request<any>(`/credentials/${credentialId}/share`, { method: 'POST', body: JSON.stringify({ categories }) }); }
export async function getCredential(credentialId: string) { return request<any>(`/credentials/${credentialId}`); }
