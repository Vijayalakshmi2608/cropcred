import { useMemo, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'wouter';
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Check,
  ChevronDown,
  CircleHelp,
  ClipboardCheck,
  Coins,
  ExternalLink,
  FileCheck2,
  Filter,
  Leaf,
  Menu,
  PackageCheck,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Truck,
  WalletCards,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import type { Demand, Harvest, Listing, Order } from '../data/mockData';
import { NetworkBadge, SolanaWalletButton, WalletAddress } from './solana';
import { useSolanaWallet } from '../contexts/SolanaWalletContext';

export const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: Sparkles, group: 'Operate' },
  { href: '/harvests', label: 'Harvests', icon: Leaf, group: 'Operate' },
  { href: '/marketplace', label: 'Marketplace', icon: PackageCheck, group: 'Operate' },
  { href: '/b2b', label: 'B2B Demand', icon: ClipboardCheck, group: 'Operate' },
  { href: '/orders', label: 'Orders', icon: Truck, group: 'Operate' },
  { href: '/passport', label: 'Economic Passport', icon: ShieldCheck, group: 'Trust' },
  { href: '/verify/CR-CRED-00001', label: 'Credentials', icon: FileCheck2, group: 'Trust' },
  { href: '/insights', label: 'Insights', icon: BarChart3, group: 'Intelligence' },
  { href: '/profile', label: 'Profile', icon: WalletCards, group: 'Account' },
];

export function StatusBadge({ status, compact = false }: { status: string; compact?: boolean }) {
  const tone = status === 'VERIFIED' || status === 'COMPLETED' || status === 'PAYMENT VERIFIED' || status === 'DELIVERY CONFIRMED'
    ? 'verified'
    : status === 'PENDING' || status === 'ORDER PLACED' || status === 'REGISTERED' ? 'pending' : 'neutral';
  return <span className={`status-badge ${tone} ${compact ? 'compact' : ''}`}><span className="status-dot" />{status}</span>;
}

export function SectionHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="section-heading"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>;
}

export function MetricCard({ label, value, trend, trendLabel, icon: Icon, tone = 'copper', category, source }: { label: string; value: string; trend?: string; trendLabel?: string; icon: typeof Leaf; tone?: string; category?: string; source?: string }) {
  return <div className={`metric-card tone-${tone}`}><div className="metric-top"><span className="metric-label">{label}</span><span className="metric-icon"><Icon size={17} strokeWidth={1.7} /></span></div><div className="metric-value">{value}</div>{category && <div className="metric-provenance"><b>{category}</b>{source && <span>{source}</span>}</div>}{trend && <div className="metric-trend"><ArrowUpRight size={13} /> <strong>{trend}</strong><span>{trendLabel}</span></div>}</div>;
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [location] = useLocation();
  const groups = Array.from(new Set(navItems.map((item) => item.group)));
  return <aside className={`sidebar ${open ? 'open' : ''}`}><div className="brand"><div className="brand-mark"><span /><span /><span /></div><div><div className="brand-name">cropcred</div><div className="brand-tag">economic passport</div></div><button className="mobile-close" onClick={onClose} aria-label="Close menu"><X size={18} /></button></div><div className="sidebar-rule" /><nav className="primary-nav">{groups.map((group) => <div className="nav-group" key={group}><div className="nav-label">{group}</div>{navItems.filter((item) => item.group === group).map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={onClose} className={`nav-item ${location === href || (href !== '/dashboard' && location.startsWith(href)) ? 'active' : ''}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{href === '/passport' && <span className="nav-pulse" />}</Link>)}</div>)}</nav><div className="sidebar-bottom"><div className="nav-label">Support</div><Link href="/profile" onClick={onClose} className="nav-item"><CircleHelp size={17} strokeWidth={1.8} /><span>Help centre</span></Link><button className="nav-item" onClick={() => window.alert('Settings will be connected in a future phase.')}><Settings size={17} strokeWidth={1.8} /><span>Settings</span></button><div className="sidebar-status"><div className="pulse-dot" /><div><strong>Demo workspace</strong><span>Devnet + local evidence</span></div></div></div></aside>;
}

export function Topbar({ title, subtitle, onMenu }: { title: string; subtitle?: string; onMenu: () => void }) {
  const { connected, publicKey, network } = useSolanaWallet();
  return <header className="topbar"><div className="topbar-heading"><button className="mobile-menu" onClick={onMenu} aria-label="Open menu"><Menu size={20} /></button><div><div className="topbar-kicker">CropCred workspace</div><h1>{title}</h1>{subtitle && <span>{subtitle}</span>}</div></div><div className="topbar-actions"><label className="top-search"><Search size={16} /><input placeholder="Search activity" aria-label="Search activity" /></label><button className="icon-button has-dot" aria-label="Notifications"><Bell size={18} /></button>{connected ? <div className="wallet-chip connected-chip"><span className="wallet-status" /> <span><strong><WalletAddress address={publicKey} /></strong><small><NetworkBadge wrong={network === 'wrong-network'} /></small></span><ChevronDown size={14} /></div> : <SolanaWalletButton compact />}<div className="avatar">AK</div></div></header>;
}

export function AppShell({ children, title, subtitle }: { children: ReactNode; title: string; subtitle?: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return <div className="app-shell"><Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />{menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Close menu" />}<main className="main-shell"><Topbar title={title} subtitle={subtitle} onMenu={() => setMenuOpen(true)} /><div className="page-content">{children}</div></main></div>;
}

export function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  return <div className="toast"><span className="toast-check"><Check size={14} /></span><span>{message}</span><button onClick={onClose} aria-label="Dismiss"><X size={14} /></button></div>;
}

export function Modal({ title, body, onClose, actionLabel }: { title: string; body: ReactNode; onClose: () => void; actionLabel?: string }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><div className="modal"><button className="modal-close" onClick={onClose} aria-label="Close"><X size={17} /></button><div className="modal-icon"><ShieldCheck size={22} /></div><div className="eyebrow">Phase 1 note</div><h3>{title}</h3><p>{body}</p><button className="button primary full" onClick={onClose}>{actionLabel || 'Understood'}</button></div></div>;
}

export function Timeline({ items }: { items: Array<{ label: string; detail: string; date: string; icon?: string; tone?: string }> }) {
  const icons: Record<string, typeof Leaf> = { harvest: Leaf, order: PackageCheck, payment: Coins, delivery: Truck };
  return <div className="timeline">{items.map((item, index) => { const Icon = icons[item.icon || 'harvest'] || Check; return <div className="timeline-item" key={`${item.label}-${index}`}><div className={`timeline-icon ${item.tone || 'copper'}`}><Icon size={16} strokeWidth={1.8} /></div><div className="timeline-copy"><strong>{item.label}</strong><span>{item.detail}</span></div><time>{item.date}</time></div>; })}</div>;
}

export function ProofFlow({ compact = false }: { compact?: boolean }) {
  const steps = [{ label: 'Harvest', icon: Leaf }, { label: 'Order', icon: PackageCheck }, { label: 'Payment', icon: Coins }, { label: 'Delivery', icon: Truck }, { label: 'Economic proof', icon: ShieldCheck }];
  return <div className={`proof-flow ${compact ? 'compact' : ''}`}>{steps.map(({ label, icon: Icon }, index) => <div className="proof-step" key={label}><div className={`proof-node ${index === steps.length - 1 ? 'final' : ''}`}><Icon size={compact ? 16 : 18} /></div><span>{label}</span>{index < steps.length - 1 && <div className="proof-line" />}</div>)}</div>;
}

export function HarvestRow({ harvest, onSelect }: { harvest: Harvest; onSelect?: () => void }) {
  return <button className="harvest-row" onClick={onSelect}><div className="row-id"><span className="crop-token">{harvest.crop.slice(0, 2).toUpperCase()}</span><div><strong>{harvest.id}</strong><span>{harvest.location}</span></div></div><span className="row-crop">{harvest.crop}</span><span>{harvest.quantity} {harvest.unit}</span><span>{harvest.date}</span><span>{harvest.price}</span><StatusBadge status={harvest.status} /></button>;
}

export function HarvestPassportCard({ harvest, onClick }: { harvest: Harvest; onClick?: () => void }) {
  return <button className="harvest-card" onClick={onClick}><div className="harvest-card-top"><div className="crop-art"><Leaf size={25} strokeWidth={1.5} /></div><StatusBadge status={harvest.status} /></div><div className="harvest-card-body"><div className="eyebrow">{harvest.id}</div><h3>{harvest.crop}</h3><div className="harvest-quantity">{harvest.quantity} <small>{harvest.unit}</small></div><div className="harvest-meta"><span>Harvested {harvest.date}</span><strong>{harvest.price}</strong></div></div><div className="harvest-card-footer"><span>View harvest passport</span><ArrowUpRight size={15} /></div></button>;
}

export function MarketplaceCard({ listing, onClick }: { listing: Listing; onClick: () => void }) {
  return <article className="market-card"><div className="market-visual"><div className="market-orbit orbit-one" /><div className="market-orbit orbit-two" /><span>{listing.crop.slice(0, 1)}</span><div className="market-verified"><Check size={12} /> Verified harvest</div></div><div className="market-body"><div className="market-title-row"><div><div className="eyebrow">{listing.listingId}</div><h3>{listing.crop}</h3></div><button className="mini-arrow" onClick={onClick} aria-label={`View ${listing.crop}`}><ArrowUpRight size={16} /></button></div><div className="market-specs"><div><span>Available</span><strong>{listing.available} {listing.unit}</strong></div><div><span>Expected price</span><strong>{listing.price}</strong></div></div><div className="market-footer"><span>Harvest {listing.date}</span><button className="text-link" onClick={onClick}>View listing <ArrowUpRight size={14} /></button></div></div></article>;
}

export function DemandCard({ demand, onOffer }: { demand: Demand; onOffer: () => void }) {
  return <article className="demand-card"><div className="demand-top"><span className="buyer-chip"><span className="buyer-chip-dot" />{demand.buyerType}</span><span className={demand.dueTone === 'urgent' ? 'due urgent' : 'due'}>{demand.due}</span></div><div className="demand-main"><div><div className="eyebrow">{demand.id}</div><h3>{demand.crop}</h3><p>{demand.buyer}</p></div><div className="demand-price">{demand.price}<span>target range</span></div></div><div className="demand-grid"><div><span>Volume</span><strong>{demand.quantity}</strong></div><div><span>Delivery</span><strong>{demand.location}</strong></div></div><button className="button outline full" onClick={onOffer}>Submit offer <ArrowUpRight size={15} /></button></article>;
}

export function OrderCard({ order, onClick }: { order: Order; onClick?: () => void }) {
  const stages = ['ORDER PLACED', 'PAYMENT VERIFIED', 'DELIVERY CONFIRMED', 'COMPLETED'];
  const activeIndex = stages.indexOf(order.status);
  return <article className="order-card"><div className="order-card-header"><div><div className="eyebrow">{order.id}</div><h3>{order.crop} <span>· {order.quantity}</span></h3></div><div className="order-amount">{order.amount}</div></div><div className="order-details"><span>Buyer <strong>{order.buyer}</strong></span><span>{order.date}</span></div><div className="order-progress">{stages.map((stage, index) => <div key={stage} className={`order-stage ${index <= activeIndex ? 'active' : ''}`}><span className="stage-dot">{index < activeIndex ? <Check size={10} /> : index === activeIndex ? <span /> : null}</span><span>{stage.replace(' VERIFIED', '').replace(' CONFIRMED', '')}</span></div>)}</div><div className="order-card-footer"><span className="awaiting"><span className="wallet-status" />{order.wallet}</span>{onClick && <button className="text-link" onClick={onClick}>View order <ArrowUpRight size={14} /></button>}</div></article>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><FileCheck2 size={22} /></div><h3>{title}</h3><p>{description}</p>{action}</div>;
}

export function FilterBar({ values, onChange }: { values: string[]; onChange: (value: string) => void }) {
  return <div className="filter-bar"><div className="filter-label"><Filter size={14} /> Filters</div>{values.map((value) => <button key={value} className="filter-pill" onClick={() => onChange(value)}>{value}<ChevronDown size={13} /></button>)}</div>;
}

export function PageFrame({ children, className = '' }: { children: ReactNode; className?: string }) { return <div className={`page-frame ${className}`}>{children}</div>; }

export function useLocalFilter<T>(items: T[], search: string, fields: Array<keyof T>) {
  return useMemo(() => items.filter((item) => fields.some((field) => String(item[field]).toLowerCase().includes(search.toLowerCase()))), [items, search, fields]);
}
