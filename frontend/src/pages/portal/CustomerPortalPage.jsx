import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  CreditCard,
  FileText,
  Layers,
  PauseCircle,
  PlayCircle,
  Printer,
  UserCheck,
} from 'lucide-react';
import {
  extractErrorMessage,
  invoicesApi,
  paymentsApi,
  quotationsApi,
  reportsApi,
  subscriptionsApi,
} from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import {
  LoadingState,
  MetricCard,
  Modal,
  StatusBadge,
  ToastBanner,
} from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const CustomerPortalPage = () => {
  const [bundle, setBundle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [payInvoice, setPayInvoice] = useState(null);
  const [payAmount, setPayAmount] = useState('');
  const [payMethod, setPayMethod] = useState('credit_card');

  const loadPortal = async () => {
    setLoading(true);
    try {
      const data = await reportsApi.portal();
      setBundle(data);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortal();
  }, []);

  const handleConfirmQuote = async (quote) => {
    try {
      const sub = await quotationsApi.confirm(quote.id, { activate_immediately: true });
      setToast({
        type: 'success',
        message: `Quotation ${quote.quotation_number} confirmed! Subscription ${sub.subscription_number} is now active.`,
      });
      loadPortal();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleSubAction = async (sub, label, fn) => {
    try {
      await fn(sub.id);
      setToast({ type: 'success', message: `${sub.subscription_number}: ${label} completed.` });
      loadPortal();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handlePrintInvoice = async (inv) => {
    try {
      const html = await invoicesApi.getPrintHtml(inv.id);
      const win = window.open('', '_blank');
      if (win) {
        win.document.write(html);
        win.document.close();
      }
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handlePaySubmit = async (e) => {
    e.preventDefault();
    if (!payInvoice) return;
    try {
      const idemKey = `portal-${payInvoice.id}-${Date.now()}`;
      await paymentsApi.record(
        {
          invoice_id: payInvoice.id,
          method: payMethod,
          amount: payAmount,
          note: 'Customer self-service portal payment',
          idempotency_key: idemKey,
        },
        idemKey
      );
      setToast({
        type: 'success',
        message: `Payment of ${formatCurrency(payAmount)} recorded for ${payInvoice.invoice_number}.`,
      });
      setPayInvoice(null);
      loadPortal();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  if (loading && !bundle) return <LoadingState label="Loading your customer portal..." />;

  const cust = bundle?.customer;
  const subscriptions = bundle?.subscriptions || [];
  const quotations = bundle?.quotations || [];
  const invoices = bundle?.invoices || [];
  const payments = bundle?.payments || [];

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome, {cust?.name || 'Valued Customer'}
          </h1>
          <p className="text-xs text-slate-400">
            {cust?.company_name ? `${cust.company_name} — ` : ''}Self-Service Subscription,
            Quotation, Invoice & Payment Portal (Strictly Isolated to Your Account)
          </p>
        </div>
      </div>

      {/* Customer KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="My Active Subscriptions"
          value={cust?.active_subscriptions_count || 0}
          subtitle={`${subscriptions.length} total subscriptions`}
          icon={Layers}
          accent="indigo"
        />
        <MetricCard
          title="Total Billed to Date"
          value={formatCurrency(cust?.total_billed)}
          subtitle={`${invoices.length} invoices issued`}
          icon={FileText}
          accent="cyan"
        />
        <MetricCard
          title="Current Balance Due"
          value={formatCurrency(cust?.outstanding_balance)}
          subtitle={`${payments.length} payments recorded`}
          icon={CreditCard}
          accent={Number(cust?.outstanding_balance) > 0 ? 'rose' : 'emerald'}
        />
      </div>

      {/* Quotations Section */}
      {quotations.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-white">My Quotations</h2>
          <DataTable
            columns={[
              { header: 'Quote #', accessor: 'quotation_number' },
              { header: 'Plan', accessor: 'plan_name' },
              { header: 'Valid Until', accessor: 'valid_until' },
              {
                header: 'Total',
                render: (r) => (
                  <span className="font-bold text-emerald-300">{formatCurrency(r.total)}</span>
                ),
              },
              {
                header: 'Status',
                render: (r) => <StatusBadge status={r.status} />,
              },
              {
                header: 'Action',
                render: (r) =>
                  r.status === 'sent' || r.status === 'draft' ? (
                    <button
                      onClick={() => handleConfirmQuote(r)}
                      className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white inline-flex items-center gap-1"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Accept & Activate
                    </button>
                  ) : (
                    <span className="text-xs text-slate-500">Confirmed</span>
                  ),
              },
            ]}
            data={quotations}
          />
        </div>
      )}

      {/* Subscriptions Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-white">My Subscriptions</h2>
        <DataTable
          emptyTitle="You have no subscriptions yet."
          columns={[
            {
              header: 'Subscription #',
              render: (r) => (
                <span className="font-mono font-semibold text-white">{r.subscription_number}</span>
              ),
            },
            { header: 'Plan', accessor: 'plan_name' },
            {
              header: 'Interval',
              render: (r) => <span className="uppercase text-xs">{r.billing_interval}</span>,
            },
            { header: 'Next Billing Date', accessor: 'next_billing_date' },
            {
              header: 'Recurring Total',
              render: (r) => (
                <span className="font-bold text-emerald-300">
                  {formatCurrency(r.recurring_total)}
                </span>
              ),
            },
            {
              header: 'State',
              render: (r) => <StatusBadge status={r.state} />,
            },
            {
              header: 'Manage',
              render: (r) => (
                <div className="flex items-center gap-2">
                  {r.state === 'active' && (
                    <button
                      onClick={() => handleSubAction(r, 'Paused', subscriptionsApi.pause)}
                      className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 text-xs inline-flex items-center gap-1"
                    >
                      <PauseCircle className="w-3 h-3" /> Pause
                    </button>
                  )}
                  {r.state === 'paused' && (
                    <button
                      onClick={() => handleSubAction(r, 'Resumed', subscriptionsApi.resume)}
                      className="px-2.5 py-1 rounded bg-emerald-600 text-white text-xs inline-flex items-center gap-1"
                    >
                      <PlayCircle className="w-3 h-3" /> Resume
                    </button>
                  )}
                </div>
              ),
            },
          ]}
          data={subscriptions}
        />
      </div>

      {/* Invoices Section */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-white">My Invoices</h2>
        <DataTable
          emptyTitle="No invoices issued yet."
          columns={[
            {
              header: 'Invoice #',
              render: (r) => (
                <span className="font-mono font-semibold text-white">{r.invoice_number}</span>
              ),
            },
            {
              header: 'Billing Period',
              render: (r) => `${r.billing_period_start} → ${r.billing_period_end}`,
            },
            { header: 'Due Date', accessor: 'due_date' },
            {
              header: 'Total',
              render: (r) => formatCurrency(r.total),
            },
            {
              header: 'Balance Due',
              render: (r) => (
                <span
                  className={
                    Number(r.amount_due) > 0 ? 'font-bold text-rose-400' : 'text-emerald-400'
                  }
                >
                  {formatCurrency(r.amount_due)}
                </span>
              ),
            },
            {
              header: 'Status',
              render: (r) => <StatusBadge status={r.payment_status} />,
            },
            {
              header: 'Actions',
              render: (r) => (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePrintInvoice(r)}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 inline-flex items-center gap-1"
                  >
                    <Printer className="w-3 h-3" /> Print/PDF
                  </button>
                  {r.state === 'confirmed' && Number(r.amount_due) > 0 && (
                    <button
                      onClick={() => {
                        setPayInvoice(r);
                        setPayAmount(String(r.amount_due));
                      }}
                      className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white inline-flex items-center gap-1"
                    >
                      <CreditCard className="w-3 h-3" /> Pay Now
                    </button>
                  )}
                </div>
              ),
            },
          ]}
          data={invoices}
        />
      </div>

      {/* Pay Invoice Modal */}
      <Modal
        open={Boolean(payInvoice)}
        title={`Pay Invoice ${payInvoice?.invoice_number}`}
        onClose={() => setPayInvoice(null)}
        maxWidth="max-w-md"
      >
        <form onSubmit={handlePaySubmit} className="space-y-4">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
            <div>Invoice Total: {formatCurrency(payInvoice?.total)}</div>
            <div className="font-bold text-rose-400">
              Outstanding Balance: {formatCurrency(payInvoice?.amount_due)}
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">Amount to Pay ($)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={payInvoice?.amount_due}
              value={payAmount}
              onChange={(e) => setPayAmount(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">Payment Method</label>
            <select
              value={payMethod}
              onChange={(e) => setPayMethod(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
            >
              <option value="credit_card">Credit Card</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="upi">UPI</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setPayInvoice(null)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              Submit Payment
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

