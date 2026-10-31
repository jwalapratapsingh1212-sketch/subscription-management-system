import React, { useEffect, useState } from 'react';
import {
  FileText,
  PauseCircle,
  PlayCircle,
  Plus,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import {
  customersApi,
  discountsApi,
  extractErrorMessage,
  invoicesApi,
  plansApi,
  productsApi,
  subscriptionsApi,
  taxRulesApi,
} from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { OrderLineBuilder } from '../../components/forms/OrderLineBuilder';
import { DataTable } from '../../components/tables/DataTable';

export const SubscriptionsPage = () => {
  const [subscriptions, setSubscriptions] = useState([]);
  const [stateFilter, setStateFilter] = useState('');
  const [customers, setCustomers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);
  const [discounts, setDiscounts] = useState([]);
  const [taxRules, setTaxRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [lines, setLines] = useState([]);
  const [form, setForm] = useState({
    customer_id: '',
    plan_id: '',
    discount_id: '',
    start_date: new Date().toISOString().slice(0, 10),
    payment_terms: 'Net 14',
    initial_state: 'active',
    notes: '',
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [subs, custRes, planList, prodList, discList, taxList] = await Promise.all([
        subscriptionsApi.list({ state: stateFilter || undefined }),
        customersApi.list({ page_size: 100 }),
        plansApi.list({ is_active: true }),
        productsApi.list({ is_active: true }),
        discountsApi.list({ is_active: true }),
        taxRulesApi.list({ is_active: true }),
      ]);
      setSubscriptions(subs);
      setCustomers(custRes.items || []);
      setPlans(planList);
      setProducts(prodList);
      setDiscounts(discList);
      setTaxRules(taxList);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [stateFilter]);

  const openCreateModal = () => {
    setForm({
      customer_id: customers[0]?.id || '',
      plan_id: plans[0]?.id || '',
      discount_id: '',
      start_date: new Date().toISOString().slice(0, 10),
      payment_terms: 'Net 14',
      initial_state: 'active',
      notes: '',
    });
    setLines([
      {
        product_id: products[0]?.id || '',
        variant_id: '',
        tax_rule_id: taxRules.find((t) => t.is_default)?.id || taxRules[0]?.id || '',
        quantity: 1,
      },
    ]);
    setCreateOpen(true);
  };

  const handleCreateSubscription = async (e) => {
    e.preventDefault();
    try {
      const created = await subscriptionsApi.create({
        customer_id: Number(form.customer_id),
        plan_id: Number(form.plan_id),
        discount_id: form.discount_id ? Number(form.discount_id) : null,
        start_date: form.start_date,
        payment_terms: form.payment_terms,
        initial_state: form.initial_state,
        notes: form.notes,
        lines: lines.map((l) => ({
          product_id: Number(l.product_id),
          variant_id: l.variant_id ? Number(l.variant_id) : null,
          tax_rule_id: l.tax_rule_id ? Number(l.tax_rule_id) : null,
          quantity: Number(l.quantity),
        })),
      });
      setToast({
        type: 'success',
        message: `Subscription ${created.subscription_number} created in '${created.state}' state.`,
      });
      setCreateOpen(false);
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const performLifecycleAction = async (sub, actionName, fn) => {
    try {
      const updated = await fn(sub.id);
      setToast({
        type: 'success',
        message: `${sub.subscription_number}: ${actionName} succeeded (State → ${updated.state.toUpperCase()}).`,
      });
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleGenerateInvoice = async (sub) => {
    try {
      const inv = await invoicesApi.generate({
        subscription_id: sub.id,
        auto_confirm: true,
        advance_next_billing_date: true,
      });
      setToast({
        type: 'success',
        message: `Generated Invoice ${inv.invoice_number} for ${sub.subscription_number} (${formatCurrency(
          inv.total
        )}).`,
      });
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Subscription Lifecycle Workbench</h1>
          <p className="text-xs text-slate-400">
            State machine: Draft → Quotation → Confirmed → Active ⇄ Paused / Past Due → Closed
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
          >
            <option value="">All Lifecycle States</option>
            <option value="draft">Draft</option>
            <option value="quotation">Quotation</option>
            <option value="confirmed">Confirmed</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="past_due">Past Due</option>
            <option value="closed">Closed</option>
          </select>

          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
          >
            <Plus className="w-4 h-4" /> New Subscription
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'Subscription #',
              render: (r) => (
                <div>
                  <div className="font-mono font-semibold text-white">{r.subscription_number}</div>
                  <div className="text-xs text-slate-400">{r.customer_name}</div>
                </div>
              ),
            },
            {
              header: 'Plan & Interval',
              render: (r) => (
                <div>
                  <div className="text-slate-200">{r.plan_name}</div>
                  <div className="text-xs uppercase text-indigo-300">{r.billing_interval}</div>
                </div>
              ),
            },
            {
              header: 'Dates (Start / Next Billing / Expiry)',
              render: (r) => (
                <div className="text-xs text-slate-300 space-y-0.5">
                  <div>Start: {r.start_date}</div>
                  <div className="text-indigo-300 font-medium">
                    Next Bill: {r.next_billing_date || '—'}
                  </div>
                  <div className="text-slate-500">Expiry: {r.expiry_date || 'Evergreen'}</div>
                </div>
              ),
            },
            {
              header: 'Recurring Total',
              render: (r) => (
                <div>
                  <div className="font-bold text-emerald-300">
                    {formatCurrency(r.recurring_total)}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Tax: {formatCurrency(r.recurring_tax)} | Disc: -
                    {formatCurrency(r.recurring_discount)}
                  </div>
                </div>
              ),
            },
            {
              header: 'State',
              render: (r) => <StatusBadge status={r.state} />,
            },
            {
              header: 'Lifecycle & Billing Actions',
              render: (r) => (
                <div className="flex flex-wrap items-center gap-1.5">
                  {r.state === 'draft' && (
                    <button
                      onClick={() =>
                        performLifecycleAction(r, 'Send Quote', subscriptionsApi.sendQuote)
                      }
                      className="px-2 py-1 rounded bg-sky-600/20 text-sky-300 border border-sky-500/30 text-xs"
                    >
                      Send Quote
                    </button>
                  )}
                  {(r.state === 'draft' || r.state === 'quotation') && (
                    <button
                      onClick={() =>
                        performLifecycleAction(r, 'Confirm', subscriptionsApi.confirm)
                      }
                      className="px-2 py-1 rounded bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 text-xs"
                    >
                      Confirm
                    </button>
                  )}
                  {(r.state === 'draft' ||
                    r.state === 'quotation' ||
                    r.state === 'confirmed') && (
                    <button
                      onClick={() =>
                        performLifecycleAction(r, 'Activate', subscriptionsApi.activate)
                      }
                      className="px-2.5 py-1 rounded bg-emerald-600 text-white text-xs font-semibold inline-flex items-center gap-1"
                    >
                      <PlayCircle className="w-3 h-3" /> Activate
                    </button>
                  )}
                  {r.state === 'active' && (
                    <>
                      <button
                        onClick={() => handleGenerateInvoice(r)}
                        className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold inline-flex items-center gap-1"
                      >
                        <FileText className="w-3 h-3" /> Bill Cycle
                      </button>
                      <button
                        onClick={() =>
                          performLifecycleAction(r, 'Pause', subscriptionsApi.pause)
                        }
                        className="px-2 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs inline-flex items-center gap-1"
                      >
                        <PauseCircle className="w-3 h-3" /> Pause
                      </button>
                    </>
                  )}
                  {r.state === 'paused' && (
                    <button
                      onClick={() =>
                        performLifecycleAction(r, 'Resume', subscriptionsApi.resume)
                      }
                      className="px-2.5 py-1 rounded bg-emerald-600 text-white text-xs font-semibold inline-flex items-center gap-1"
                    >
                      <PlayCircle className="w-3 h-3" /> Resume
                    </button>
                  )}
                  {(r.state === 'active' ||
                    r.state === 'past_due' ||
                    r.state === 'closed') && (
                    <button
                      onClick={() =>
                        performLifecycleAction(r, 'Renew Term', subscriptionsApi.renew)
                      }
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-300 text-xs inline-flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" /> Renew
                    </button>
                  )}
                  {r.state !== 'closed' && (
                    <button
                      onClick={() =>
                        performLifecycleAction(r, 'Close Subscription', subscriptionsApi.close)
                      }
                      className="px-2 py-1 rounded bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-500/30 text-xs inline-flex items-center gap-1"
                    >
                      <XCircle className="w-3 h-3" /> Close
                    </button>
                  )}
                </div>
              ),
            },
          ]}
          data={subscriptions}
        />
      )}

      {/* Create Subscription Modal */}
      <Modal
        open={createOpen}
        title="Create Subscription"
        onClose={() => setCreateOpen(false)}
        maxWidth="max-w-4xl"
      >
        <form onSubmit={handleCreateSubscription} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Customer *</label>
              <select
                value={form.customer_id}
                onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                required
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.email})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Subscription Plan *</label>
              <select
                value={form.plan_id}
                onChange={(e) => setForm({ ...form, plan_id: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                required
              >
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.billing_interval}, min qty {p.minimum_quantity})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Initial Lifecycle State</label>
              <select
                value={form.initial_state}
                onChange={(e) => setForm({ ...form, initial_state: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="active">Active (Ready for Billing)</option>
                <option value="confirmed">Confirmed</option>
                <option value="quotation">Quotation</option>
                <option value="draft">Draft</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Start Date *</label>
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Discount</label>
              <select
                value={form.discount_id}
                onChange={(e) => setForm({ ...form, discount_id: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="">No Discount</option>
                {discounts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Payment Terms</label>
              <input
                type="text"
                value={form.payment_terms}
                onChange={(e) => setForm({ ...form, payment_terms: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              />
            </div>
          </div>

          <OrderLineBuilder
            lines={lines}
            setLines={setLines}
            products={products}
            taxRules={taxRules}
          />

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Create Subscription
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

