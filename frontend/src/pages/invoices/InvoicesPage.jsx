import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  CreditCard,
  Eye,
  Play,
  Printer,
  XCircle,
} from 'lucide-react';
import {
  extractErrorMessage,
  invoicesApi,
} from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const InvoicesPage = () => {
  const [invoices, setInvoices] = useState([]);
  const [stateFilter, setStateFilter] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const navigate = useNavigate();

  const loadInvoices = async () => {
    setLoading(true);
    try {
      const data = await invoicesApi.list({
        state: stateFilter || undefined,
        overdue_only: overdueOnly || undefined,
      });
      setInvoices(data);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, [stateFilter, overdueOnly]);

  const handleRunBillingBatch = async () => {
    try {
      const res = await invoicesApi.generate({ auto_confirm: true });
      setToast({
        type: 'success',
        message: `Automated billing batch finished: ${res.generated_count} invoice(s) generated, ${res.skipped_duplicates} duplicate(s) prevented.`,
      });
      loadInvoices();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleConfirm = async (inv) => {
    try {
      await invoicesApi.confirm(inv.id);
      setToast({ type: 'success', message: `Invoice ${inv.invoice_number} confirmed.` });
      loadInvoices();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleCancel = async (inv) => {
    try {
      await invoicesApi.cancel(inv.id);
      setToast({ type: 'success', message: `Invoice ${inv.invoice_number} cancelled.` });
      loadInvoices();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handlePrint = async (inv) => {
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

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Invoices & Automated Recurring Billing</h1>
          <p className="text-xs text-slate-400">
            Immutable billing-period snapshots, tax & discount breakdowns, and idempotent invoice
            generation
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-300 bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl cursor-pointer">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="rounded border-slate-700 text-rose-500"
            />
            <span>Overdue Only</span>
          </label>

          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
          >
            <option value="">All Invoice States</option>
            <option value="draft">Draft</option>
            <option value="confirmed">Confirmed</option>
            <option value="paid">Paid</option>
            <option value="cancelled">Cancelled</option>
          </select>

          <button
            onClick={handleRunBillingBatch}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg"
          >
            <Play className="w-3.5 h-3.5" /> Run Due Billing Engine
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'Invoice #',
              render: (r) => (
                <div>
                  <div className="font-mono font-semibold text-white">{r.invoice_number}</div>
                  <div className="text-xs text-slate-400">{r.customer_name}</div>
                </div>
              ),
            },
            {
              header: 'Billing Period',
              render: (r) => (
                <div className="text-xs text-slate-300">
                  <div>
                    {r.billing_period_start} → {r.billing_period_end}
                  </div>
                  <div className="text-slate-500">Sub: {r.subscription_number}</div>
                </div>
              ),
            },
            {
              header: 'Due Date',
              render: (r) => (
                <span className={r.is_overdue ? 'text-rose-400 font-semibold' : 'text-slate-300'}>
                  {r.due_date}
                </span>
              ),
            },
            {
              header: 'Total',
              render: (r) => <span className="font-bold text-white">{formatCurrency(r.total)}</span>,
            },
            {
              header: 'Paid / Balance Due',
              render: (r) => (
                <div className="text-xs">
                  <div className="text-emerald-400">Paid: {formatCurrency(r.amount_paid)}</div>
                  <div
                    className={
                      Number(r.amount_due) > 0 ? 'font-bold text-rose-400' : 'text-slate-500'
                    }
                  >
                    Due: {formatCurrency(r.amount_due)}
                  </div>
                </div>
              ),
            },
            {
              header: 'State / Payment',
              render: (r) => (
                <div className="flex flex-col gap-1 items-start">
                  <StatusBadge status={r.state} />
                  <StatusBadge status={r.payment_status} />
                </div>
              ),
            },
            {
              header: 'Actions',
              render: (r) => (
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    onClick={() => setSelectedInvoice(r)}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 inline-flex items-center gap-1"
                  >
                    <Eye className="w-3 h-3" /> Details
                  </button>
                  <button
                    onClick={() => handlePrint(r)}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-indigo-300 inline-flex items-center gap-1"
                  >
                    <Printer className="w-3 h-3" /> Print/PDF
                  </button>
                  {r.state === 'draft' && (
                    <button
                      onClick={() => handleConfirm(r)}
                      className="px-2 py-1 rounded bg-emerald-600 text-white text-xs font-semibold inline-flex items-center gap-1"
                    >
                      <CheckCircle2 className="w-3 h-3" /> Confirm
                    </button>
                  )}
                  {r.state === 'confirmed' && Number(r.amount_due) > 0 && (
                    <button
                      onClick={() => navigate(`/payments?invoice_id=${r.id}`)}
                      className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold inline-flex items-center gap-1"
                    >
                      <CreditCard className="w-3 h-3" /> Pay
                    </button>
                  )}
                  {(r.state === 'draft' ||
                    (r.state === 'confirmed' && Number(r.amount_paid) === 0)) && (
                    <button
                      onClick={() => handleCancel(r)}
                      className="px-2 py-1 rounded bg-rose-950/60 text-rose-300 border border-rose-500/30 text-xs inline-flex items-center gap-1"
                    >
                      <XCircle className="w-3 h-3" /> Cancel
                    </button>
                  )}
                </div>
              ),
            },
          ]}
          data={invoices}
        />
      )}

      {/* Invoice Detail Snapshot Modal */}
      <Modal
        open={Boolean(selectedInvoice)}
        title={`Invoice ${selectedInvoice?.invoice_number} — Historical Snapshot`}
        onClose={() => setSelectedInvoice(null)}
      >
        {selectedInvoice && (
          <div className="space-y-4 text-sm">
            <div className="flex justify-between items-start bg-slate-950 p-4 rounded-xl border border-slate-800">
              <div className="space-y-1 text-xs">
                <div className="text-sm font-bold text-white">{selectedInvoice.customer_name}</div>
                <div className="text-slate-400">{selectedInvoice.customer_email}</div>
                <div className="text-slate-400">
                  Billing Period: {selectedInvoice.billing_period_start} to{' '}
                  {selectedInvoice.billing_period_end}
                </div>
                <div className="text-slate-400">
                  Issue Date: {selectedInvoice.issue_date} | Due Date: {selectedInvoice.due_date}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <StatusBadge status={selectedInvoice.state} />
                <StatusBadge status={selectedInvoice.payment_status} />
              </div>
            </div>

            <DataTable
              columns={[
                { header: 'Description', accessor: 'description' },
                { header: 'Qty', accessor: 'quantity' },
                {
                  header: 'Snapshot Unit Price',
                  render: (l) => formatCurrency(l.unit_price),
                },
                {
                  header: 'Snapshot Tax',
                  render: (l) => `${l.tax_rate}% (${formatCurrency(l.line_tax)})`,
                },
                {
                  header: 'Line Total',
                  render: (l) => (
                    <span className="font-semibold text-white">{formatCurrency(l.line_total)}</span>
                  ),
                },
              ]}
              data={selectedInvoice.lines || []}
            />

            <div className="grid grid-cols-2 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs">
              <div className="space-y-1 text-slate-400">
                <div>Subtotal: {formatCurrency(selectedInvoice.subtotal)}</div>
                <div>Discount: -{formatCurrency(selectedInvoice.discount_amount)}</div>
                <div>Tax: {formatCurrency(selectedInvoice.tax_amount)}</div>
              </div>
              <div className="text-right space-y-1">
                <div className="text-sm font-bold text-white">
                  Total: {formatCurrency(selectedInvoice.total)}
                </div>
                <div className="text-emerald-400">
                  Paid: {formatCurrency(selectedInvoice.amount_paid)}
                </div>
                <div className="text-base font-bold text-rose-400">
                  Balance Due: {formatCurrency(selectedInvoice.amount_due)}
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

