import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CreditCard, Plus, ShieldCheck } from 'lucide-react';
import {
  extractErrorMessage,
  invoicesApi,
  paymentsApi,
} from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const PaymentsPage = () => {
  const [searchParams] = useSearchParams();
  const [payments, setPayments] = useState([]);
  const [payableInvoices, setPayableInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    invoice_id: '',
    method: 'credit_card',
    amount: '',
    payment_date: new Date().toISOString().slice(0, 10),
    reference: '',
    note: '',
    idempotency_key: '',
  });

  const generateIdempotencyKey = () =>
    `idem-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  const loadData = async () => {
    setLoading(true);
    try {
      const [payList, invList] = await Promise.all([
        paymentsApi.list(),
        invoicesApi.list({ state: 'confirmed' }),
      ]);
      setPayments(payList);
      const openInvs = invList.filter((inv) => Number(inv.amount_due) > 0);
      setPayableInvoices(openInvs);

      const preselectedId = searchParams.get('invoice_id');
      if (preselectedId) {
        const target = openInvs.find((i) => Number(i.id) === Number(preselectedId));
        if (target) {
          setForm({
            invoice_id: target.id,
            method: 'credit_card',
            amount: String(target.amount_due),
            payment_date: new Date().toISOString().slice(0, 10),
            reference: '',
            note: `Payment settlement for ${target.invoice_number}`,
            idempotency_key: generateIdempotencyKey(),
          });
          setModalOpen(true);
        }
      }
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openPaymentModal = (inv = null) => {
    const target = inv || payableInvoices[0];
    setForm({
      invoice_id: target ? target.id : '',
      method: 'credit_card',
      amount: target ? String(target.amount_due) : '',
      payment_date: new Date().toISOString().slice(0, 10),
      reference: '',
      note: target ? `Settlement for ${target.invoice_number}` : '',
      idempotency_key: generateIdempotencyKey(),
    });
    setModalOpen(true);
  };

  const handleInvoiceChange = (invoiceId) => {
    const target = payableInvoices.find((i) => Number(i.id) === Number(invoiceId));
    setForm({
      ...form,
      invoice_id: invoiceId,
      amount: target ? String(target.amount_due) : '',
    });
  };

  const handleRecordPayment = async (e) => {
    e.preventDefault();
    try {
      const res = await paymentsApi.record(
        {
          invoice_id: Number(form.invoice_id),
          method: form.method,
          amount: form.amount,
          payment_date: form.payment_date || null,
          reference: form.reference || null,
          note: form.note || null,
          idempotency_key: form.idempotency_key,
        },
        form.idempotency_key
      );
      setToast({
        type: 'success',
        message: `Recorded Payment ${res.payment_number} (${formatCurrency(
          res.amount
        )}). Remaining Invoice Balance: ${formatCurrency(res.invoice_amount_due)}.`,
      });
      setModalOpen(false);
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Payments & Balance Reconciliation</h1>
          <p className="text-xs text-slate-400">
            Idempotent payment processing, partial & full invoice allocation, and overpayment
            protection
          </p>
        </div>

        <button
          onClick={() => openPaymentModal()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
        >
          <Plus className="w-4 h-4" /> Record Payment
        </button>
      </div>

      {/* Open Receivables Banner */}
      {payableInvoices.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Confirmed Invoices Awaiting Settlement ({payableInvoices.length})
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {payableInvoices.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800"
              >
                <div>
                  <div className="font-mono font-bold text-white text-xs">
                    {inv.invoice_number}
                  </div>
                  <div className="text-xs text-slate-400">{inv.customer_name}</div>
                  <div className="text-xs text-rose-400 font-semibold mt-0.5">
                    Due: {formatCurrency(inv.amount_due)} (of {formatCurrency(inv.total)})
                  </div>
                </div>
                <button
                  onClick={() => openPaymentModal(inv)}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                >
                  Settle
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'Payment #',
              render: (r) => (
                <span className="font-mono font-semibold text-white">{r.payment_number}</span>
              ),
            },
            {
              header: 'Invoice #',
              render: (r) => (
                <span className="font-mono text-indigo-300">{r.invoice_number}</span>
              ),
            },
            { header: 'Customer', accessor: 'customer_name' },
            {
              header: 'Method',
              render: (r) => (
                <span className="uppercase text-xs text-slate-300">
                  {String(r.method).replace(/_/g, ' ')}
                </span>
              ),
            },
            {
              header: 'Amount Paid',
              render: (r) => (
                <span className="font-bold text-emerald-300">{formatCurrency(r.amount)}</span>
              ),
            },
            { header: 'Payment Date', accessor: 'payment_date' },
            {
              header: 'Idempotency Key',
              render: (r) => (
                <span className="font-mono text-[11px] text-slate-400">{r.idempotency_key}</span>
              ),
            },
            {
              header: 'Status',
              render: (r) => <StatusBadge status={r.status} />,
            },
          ]}
          data={payments}
        />
      )}

      {/* Record Payment Modal */}
      <Modal
        open={modalOpen}
        title="Record Invoice Payment (Idempotent Reconciliation)"
        onClose={() => setModalOpen(false)}
        maxWidth="max-w-lg"
      >
        <form onSubmit={handleRecordPayment} className="space-y-4">
          <div>
            <label className="block text-xs text-slate-300 mb-1">Select Confirmed Invoice *</label>
            <select
              value={form.invoice_id}
              onChange={(e) => handleInvoiceChange(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              required
            >
              <option value="">Choose an open invoice...</option>
              {payableInvoices.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.invoice_number} — {inv.customer_name} (Balance Due:{' '}
                  {formatCurrency(inv.amount_due)})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">
                Payment Amount ($) * (Partial or Full)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Payment Method *</label>
              <select
                value={form.method}
                onChange={(e) => setForm({ ...form, method: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              >
                <option value="credit_card">Credit Card</option>
                <option value="bank_transfer">Bank Transfer (ACH)</option>
                <option value="wire">Wire Transfer</option>
                <option value="upi">UPI / Instant Pay</option>
                <option value="check">Corporate Check</option>
                <option value="cash">Cash</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Payment Date</label>
              <input
                type="date"
                value={form.payment_date}
                onChange={(e) => setForm({ ...form, payment_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Transaction Reference</label>
              <input
                type="text"
                value={form.reference}
                onChange={(e) => setForm({ ...form, reference: e.target.value })}
                placeholder="TXN-99201"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-300 mb-1 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              Idempotency Key (Prevents Duplicate Charge on Retries)
            </label>
            <input
              type="text"
              value={form.idempotency_key}
              onChange={(e) => setForm({ ...form, idempotency_key: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-300 font-mono"
              required
            />
          </div>

          <div>
            <label className="block text-xs text-slate-300 mb-1">Payment Notes</label>
            <input
              type="text"
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              Confirm & Reconcile Payment
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

