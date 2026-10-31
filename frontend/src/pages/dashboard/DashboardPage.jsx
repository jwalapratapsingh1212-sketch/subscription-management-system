import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Banknote,
  Calendar,
  CheckCircle2,
  DollarSign,
  Layers,
  Play,
  ShieldPlus,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  authApi,
  extractErrorMessage,
  invoicesApi,
  reportsApi,
} from '../../services/api/client';
import { useAuth } from '../../services/auth/AuthContext';
import { formatCurrency, validatePasswordPolicy } from '../../services/validators';
import {
  LoadingState,
  MetricCard,
  Modal,
  StatusBadge,
  ToastBanner,
} from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const DashboardPage = () => {
  const { isAdmin } = useAuth();
  const [summary, setSummary] = useState(null);
  const [overdueList, setOverdueList] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  // Admin-only Staff Provisioning Modal
  const [staffModalOpen, setStaffModalOpen] = useState(false);
  const [staffForm, setStaffForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'staff',
  });

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const [sumData, ovData, logsData] = await Promise.all([
        reportsApi.dashboard(params),
        reportsApi.overdue(),
        reportsApi.auditLogs({ limit: 12 }),
      ]);
      setSummary(sumData);
      setOverdueList(ovData);
      setAuditLogs(logsData);
      if (isAdmin) {
        const uList = await authApi.listUsers();
        setUsersList(uList);
      }
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleRunBillingCycle = async () => {
    try {
      const res = await invoicesApi.generate({ auto_confirm: true });
      setToast({
        type: 'success',
        message: `Billing cycle completed: ${res.generated_count} new invoice(s) generated, ${res.skipped_duplicates} duplicate(s) skipped.`,
      });
      loadDashboard();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleCreateStaff = async (e) => {
    e.preventDefault();
    const passErr = validatePasswordPolicy(staffForm.password);
    if (passErr) {
      setToast({ type: 'error', message: passErr });
      return;
    }
    try {
      await authApi.createStaff(staffForm);
      setToast({
        type: 'success',
        message: `Provisioned ${staffForm.role.toUpperCase()} account for ${staffForm.email}.`,
      });
      setStaffModalOpen(false);
      setStaffForm({ full_name: '', email: '', password: '', role: 'staff' });
      loadDashboard();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  if (loading && !summary) return <LoadingState label="Aggregating enterprise financial metrics..." />;

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      {/* Top Header & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Executive Finance & Billing Dashboard</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time MRR, Billed Receivables, Cash Collections, and Pro-Rata Revenue Recognition
            (Query time: {summary?.query_execution_ms} ms)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none"
            />
            <span className="text-slate-600">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none"
            />
            <button
              onClick={loadDashboard}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 font-semibold"
            >
              Filter
            </button>
          </div>

          <button
            onClick={handleRunBillingCycle}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20"
          >
            <Play className="w-3.5 h-3.5" />
            Run Automated Billing Cycle
          </button>

          {isAdmin && (
            <button
              onClick={() => setStaffModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/20"
            >
              <ShieldPlus className="w-3.5 h-3.5" />
              Provision Staff Account
            </button>
          )}
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Monthly Recurring Revenue (MRR)"
          value={formatCurrency(summary?.monthly_recurring_revenue)}
          subtitle={`ARR: ${formatCurrency(summary?.annual_recurring_revenue)}`}
          icon={TrendingUp}
          accent="indigo"
        />
        <MetricCard
          title="Active Subscriptions"
          value={`${summary?.active_subscriptions} / ${summary?.total_subscriptions}`}
          subtitle={`${summary?.active_customers} active customers`}
          icon={Layers}
          accent="cyan"
        />
        <MetricCard
          title="Cash Collected (Payments)"
          value={formatCurrency(summary?.cash_collected)}
          subtitle={`Billed Total: ${formatCurrency(summary?.billed_revenue)}`}
          icon={Banknote}
          accent="emerald"
        />
        <MetricCard
          title="Outstanding Receivables"
          value={formatCurrency(summary?.outstanding_receivables)}
          subtitle={`${summary?.overdue_invoices_count} overdue (${formatCurrency(
            summary?.overdue_amount
          )})`}
          icon={AlertTriangle}
          accent="rose"
        />
      </div>

      {/* Accounting Separation Banner: Billed vs Cash vs Recognized vs Deferred */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-bold text-white">
              Financial Accounting Breakdown (Billed vs. Cash vs. Service-Period Recognition)
            </h2>
            <p className="text-xs text-slate-400">
              Separates invoice billings from cash collections and time-prorated service-period
              recognition (ASC 606 / IFRS 15 preview)
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mt-2">
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-[11px] text-slate-400 uppercase font-semibold">
              1. Gross Billed (Incl. Tax)
            </div>
            <div className="text-lg font-bold text-white mt-1">
              {formatCurrency(summary?.billed_revenue)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Net Ex-Tax: {formatCurrency(summary?.billed_net_ex_tax)}
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-[11px] text-emerald-400 uppercase font-semibold">
              2. Cash Collected
            </div>
            <div className="text-lg font-bold text-emerald-300 mt-1">
              {formatCurrency(summary?.cash_collected)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Settled payment allocations
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-[11px] text-indigo-400 uppercase font-semibold">
              3. Earned Revenue (Pro-Rata)
            </div>
            <div className="text-lg font-bold text-indigo-300 mt-1">
              {formatCurrency(summary?.recognized_revenue_pro_rata)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Recognized over elapsed service days
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-[11px] text-amber-400 uppercase font-semibold">
              4. Deferred Revenue (Unearned)
            </div>
            <div className="text-lg font-bold text-amber-300 mt-1">
              {formatCurrency(summary?.deferred_revenue_unearned)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Remaining future service obligation
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">
            Revenue Trends: Billed vs. Cash Collected vs. Recognized
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={summary?.revenue_trends || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="period" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="billed_revenue"
                  name="Billed Revenue"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.2}
                />
                <Area
                  type="monotone"
                  dataKey="cash_collected"
                  name="Cash Collected"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.2}
                />
                <Area
                  type="monotone"
                  dataKey="recognized_revenue"
                  name="Recognized (Pro-Rata)"
                  stroke="#f59e0b"
                  fill="#f59e0b"
                  fillOpacity={0.15}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">
            Subscription State Distribution
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary?.subscription_state_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="state" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '12px',
                  }}
                />
                <Bar dataKey="count" name="Subscriptions" fill="#818cf8" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Overdue Invoices Table */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400" />
          Overdue Invoices & Dunning Watchlist ({overdueList.length})
        </h3>
        <DataTable
          emptyTitle="No overdue invoices — all receivables are within payment terms."
          columns={[
            {
              header: 'Invoice #',
              render: (r) => <span className="font-mono font-semibold text-white">{r.invoice_number}</span>,
            },
            { header: 'Customer', accessor: 'customer_name' },
            { header: 'Subscription', accessor: 'subscription_number' },
            { header: 'Due Date', accessor: 'due_date' },
            {
              header: 'Aging',
              render: (r) => (
                <span className="text-rose-400 font-semibold">{r.days_overdue} days overdue</span>
              ),
            },
            {
              header: 'Total',
              render: (r) => formatCurrency(r.total),
            },
            {
              header: 'Paid',
              render: (r) => formatCurrency(r.amount_paid),
            },
            {
              header: 'Balance Due',
              render: (r) => (
                <span className="font-bold text-rose-300">{formatCurrency(r.amount_due)}</span>
              ),
            },
          ]}
          data={overdueList}
          keyField="invoice_id"
        />
      </div>

      {/* Admin-Only System Users & Immutable Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {isAdmin && (
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-white">
              System Users & RBAC Roles (Admin View)
            </h3>
            <DataTable
              columns={[
                { header: 'Name', accessor: 'full_name' },
                { header: 'Email', accessor: 'email' },
                {
                  header: 'Role',
                  render: (r) => <StatusBadge status={r.role} />,
                },
                {
                  header: 'Status',
                  render: (r) => (
                    <StatusBadge status={r.is_active ? 'active' : 'closed'} />
                  ),
                },
              ]}
              data={usersList}
            />
          </div>
        )}

        <div className={`space-y-3 ${!isAdmin ? 'lg:col-span-2' : ''}`}>
          <h3 className="text-sm font-bold text-white">Immutable Financial Audit Trail</h3>
          <DataTable
            columns={[
              {
                header: 'Timestamp',
                render: (r) => new Date(r.timestamp).toLocaleString(),
              },
              { header: 'Actor', accessor: 'actor_email' },
              {
                header: 'Action',
                render: (r) => (
                  <span className="font-mono text-xs text-indigo-300">{r.action}</span>
                ),
              },
              {
                header: 'Entity',
                render: (r) => `${r.entity_type} #${r.entity_id}`,
              },
            ]}
            data={auditLogs}
          />
        </div>
      </div>

      {/* Admin Staff Provisioning Modal */}
      <Modal
        open={staffModalOpen}
        title="Provision Internal Staff / Admin Account"
        onClose={() => setStaffModalOpen(false)}
        maxWidth="max-w-md"
      >
        <form onSubmit={handleCreateStaff} className="space-y-4">
          <div>
            <label className="block text-xs text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              value={staffForm.full_name}
              onChange={(e) => setStaffForm({ ...staffForm, full_name: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">Work Email</label>
            <input
              type="email"
              value={staffForm.email}
              onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">
              Initial Password (8+ chars, upper, lower, special)
            </label>
            <input
              type="password"
              value={staffForm.password}
              onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">Role</label>
            <select
              value={staffForm.role}
              onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
            >
              <option value="staff">Internal Staff (Operations & Billing)</option>
              <option value="admin">System Administrator</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setStaffModalOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white"
            >
              Create Account
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

