import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Boxes,
  CalendarClock,
  CreditCard,
  FileSpreadsheet,
  FileText,
  Layers,
  LogOut,
  Percent,
  ShieldCheck,
  UserCircle,
  Users,
} from 'lucide-react';
import { useAuth } from '../../services/auth/AuthContext';
import { StatusBadge } from '../common/UI';

export const AppLayout = ({ children }) => {
  const { user, isStaff, isCustomer, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const staffNav = [
    { to: '/dashboard', label: 'Finance Dashboard', icon: BarChart3 },
    { to: '/customers', label: 'Customers', icon: Users },
    { to: '/products', label: 'Products & Variants', icon: Boxes },
    { to: '/plans', label: 'Subscription Plans', icon: CalendarClock },
    { to: '/quotations', label: 'Quotations', icon: FileSpreadsheet },
    { to: '/subscriptions', label: 'Subscriptions', icon: Layers },
    { to: '/invoices', label: 'Invoices & Billing', icon: FileText },
    { to: '/discounts', label: 'Discounts & Taxes', icon: Percent },
    { to: '/payments', label: 'Payments', icon: CreditCard },
  ];

  const customerNav = [
    { to: '/portal', label: 'My Customer Portal', icon: UserCircle },
  ];

  const navItems = isCustomer ? customerNav : staffNav;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col shrink-0">
        <div className="p-5 border-b border-slate-800 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-white tracking-tight text-sm">SubManage Pro</div>
            <div className="text-[11px] text-slate-400">Enterprise Billing OS</div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  active
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800 bg-slate-900/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-white truncate max-w-[140px]">
              {user?.full_name || user?.email}
            </span>
            <StatusBadge status={user?.role} />
          </div>
          <div className="text-xs text-slate-400 truncate mb-3">{user?.email}</div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-rose-950/80 text-slate-300 hover:text-rose-200 border border-slate-700 hover:border-rose-500/40 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-slate-800 bg-slate-900/50 px-6 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            {isStaff
              ? 'Role-Based Access: Internal Operations & Finance Workbench'
              : 'Customer Self-Service Subscription & Billing Portal'}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>Precision: NUMERIC(12,2)</span>
            <span className="text-slate-700">|</span>
            <span className="text-emerald-400 font-medium">● API Connected</span>
          </div>
        </header>
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
};

