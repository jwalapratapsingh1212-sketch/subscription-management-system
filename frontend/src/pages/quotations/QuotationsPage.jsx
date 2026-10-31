import React, { useEffect, useState } from 'react';
import { CheckCircle2, Eye, FilePlus, Layers } from 'lucide-react';
import {
  customersApi,
  discountsApi,
  extractErrorMessage,
  plansApi,
  productsApi,
  quotationsApi,
  taxRulesApi,
} from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { OrderLineBuilder } from '../../components/forms/OrderLineBuilder';
import { DataTable } from '../../components/tables/DataTable';

export const QuotationsPage = () => {
  const [quotations, setQuotations] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);
  const [discounts, setDiscounts] = useState([]);
  const [taxRules, setTaxRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [detailQuote, setDetailQuote] = useState(null);
  const [lines, setLines] = useState([]);
  const [form, setForm] = useState({
    customer_id: '',
    plan_id: '',
    template_id: '',
    discount_id: '',
    valid_until: '',
    payment_terms: 'Net 14',
    notes: '',
    status: 'sent',
  });

  const loadAll = async () => {
    setLoading(true);
    try {
      const [qList, tplList, custRes, planList, prodList, discList, taxList] =
        await Promise.all([
          quotationsApi.list(),
          quotationsApi.listTemplates(),
          customersApi.list({ page_size: 100 }),
          plansApi.list({ is_active: true }),
          productsApi.list({ is_active: true }),
          discountsApi.list({ is_active: true }),
          taxRulesApi.list({ is_active: true }),
        ]);
      setQuotations(qList);
      setTemplates(tplList);
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
    loadAll();
  }, []);

  const openCreateModal = () => {
    const firstCust = customers[0]?.id || '';
    const firstPlan = plans[0]?.id || '';
    const firstProd = products[0]?.id || '';
    const defaultTax = taxRules.find((t) => t.is_default)?.id || taxRules[0]?.id || '';
    const validDate = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);

    setForm({
      customer_id: firstCust,
      plan_id: firstPlan,
      template_id: '',
      discount_id: '',
      valid_until: validDate,
      payment_terms: 'Net 14',
      notes: '',
      status: 'sent',
    });
    setLines([
      {
        product_id: firstProd,
        variant_id: '',
        tax_rule_id: defaultTax,
        quantity: 1,
      },
    ]);
    setCreateOpen(true);
  };

  const applyTemplate = (templateId) => {
    const tpl = templates.find((t) => Number(t.id) === Number(templateId));
    if (!tpl) {
      setForm({ ...form, template_id: '' });
      return;
    }
    let parsedLines = [];
    try {
      parsedLines = JSON.parse(tpl.default_lines_json || '[]');
    } catch {
      parsedLines = [];
    }
    setForm({
      ...form,
      template_id: tpl.id,
      plan_id: tpl.plan_id,
      payment_terms: tpl.payment_terms || 'Net 14',
      notes: tpl.notes || '',
    });
    if (parsedLines.length > 0) {
      setLines(
        parsedLines.map((l) => ({
          product_id: l.product_id,
          variant_id: l.variant_id || '',
          tax_rule_id: l.tax_rule_id || taxRules[0]?.id || '',
          quantity: Number(l.quantity || 1),
        }))
      );
    }
  };

  const handleCreateQuotation = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        customer_id: Number(form.customer_id),
        plan_id: Number(form.plan_id),
        template_id: form.template_id ? Number(form.template_id) : null,
        discount_id: form.discount_id ? Number(form.discount_id) : null,
        valid_until: form.valid_until || null,
        payment_terms: form.payment_terms,
        notes: form.notes,
        status: form.status,
        lines: lines.map((l) => ({
          product_id: Number(l.product_id),
          variant_id: l.variant_id ? Number(l.variant_id) : null,
          tax_rule_id: l.tax_rule_id ? Number(l.tax_rule_id) : null,
          quantity: Number(l.quantity),
        })),
      };
      const created = await quotationsApi.create(payload);
      setToast({
        type: 'success',
        message: `Created Quotation ${created.quotation_number} (Total: ${formatCurrency(
          created.total
        )}).`,
      });
      setCreateOpen(false);
      loadAll();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleConfirmQuote = async (quote) => {
    try {
      const sub = await quotationsApi.confirm(quote.id, { activate_immediately: true });
      setToast({
        type: 'success',
        message: `Quotation ${quote.quotation_number} confirmed and converted into Active Subscription ${sub.subscription_number}!`,
      });
      setDetailQuote(null);
      loadAll();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Quotations & Quote-to-Subscription</h1>
          <p className="text-xs text-slate-400">
            Create time-bound customer quotations from templates, apply discounts & taxes, and
            convert confirmed quotes into active subscriptions
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
        >
          <FilePlus className="w-4 h-4" /> Prepare Quotation
        </button>
      </div>

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'Quote #',
              render: (r) => (
                <span className="font-mono font-semibold text-white">{r.quotation_number}</span>
              ),
            },
            { header: 'Customer', accessor: 'customer_name' },
            { header: 'Plan', accessor: 'plan_name' },
            { header: 'Valid Until', accessor: 'valid_until' },
            {
              header: 'Subtotal',
              render: (r) => formatCurrency(r.subtotal),
            },
            {
              header: 'Discount',
              render: (r) => (
                <span className="text-amber-300">-{formatCurrency(r.discount_amount)}</span>
              ),
            },
            {
              header: 'Tax',
              render: (r) => formatCurrency(r.tax_amount),
            },
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
              header: 'Actions',
              render: (r) => (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDetailQuote(r)}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 inline-flex items-center gap-1"
                  >
                    <Eye className="w-3.5 h-3.5" /> View
                  </button>
                  {(r.status === 'draft' || r.status === 'sent') && (
                    <button
                      onClick={() => handleConfirmQuote(r)}
                      className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white inline-flex items-center gap-1"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Confirm → Subscription
                    </button>
                  )}
                </div>
              ),
            },
          ]}
          data={quotations}
        />
      )}

      {/* Create Quotation Modal */}
      <Modal
        open={createOpen}
        title="Prepare Customer Quotation"
        onClose={() => setCreateOpen(false)}
        maxWidth="max-w-4xl"
      >
        <form onSubmit={handleCreateQuotation} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">
                Apply Quotation Template (Optional)
              </label>
              <select
                value={form.template_id}
                onChange={(e) => applyTemplate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="">Custom Quote (No Template)</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

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
                    {c.name} ({c.company_name || c.email})
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
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Valid Until *</label>
              <input
                type="date"
                value={form.valid_until}
                onChange={(e) => setForm({ ...form, valid_until: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Promotional Discount</label>
              <select
                value={form.discount_id}
                onChange={(e) => setForm({ ...form, discount_id: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="">No Discount</option>
                {discounts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name} (
                    {d.discount_type === 'percentage' ? `${d.value}%` : formatCurrency(d.value)})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1">Initial Status</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="sent">Sent to Customer</option>
                <option value="draft">Draft</option>
              </select>
            </div>
          </div>

          <OrderLineBuilder
            lines={lines}
            setLines={setLines}
            products={products}
            taxRules={taxRules}
          />

          <div>
            <label className="block text-xs text-slate-300 mb-1">Commercial Terms & Notes</label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
            />
          </div>

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
              Create Quotation
            </button>
          </div>
        </form>
      </Modal>

      {/* Quote Detail Modal */}
      <Modal
        open={Boolean(detailQuote)}
        title={`Quotation ${detailQuote?.quotation_number}`}
        onClose={() => setDetailQuote(null)}
      >
        {detailQuote && (
          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between bg-slate-950 p-4 rounded-xl border border-slate-800">
              <div>
                <div className="text-xs text-slate-400">Customer</div>
                <div className="font-semibold text-white">{detailQuote.customer_name}</div>
                <div className="text-xs text-slate-400 mt-1">
                  Plan: {detailQuote.plan_name} | Valid until: {detailQuote.valid_until}
                </div>
              </div>
              <StatusBadge status={detailQuote.status} />
            </div>

            <DataTable
              columns={[
                { header: 'Description', accessor: 'description' },
                { header: 'Qty', accessor: 'quantity' },
                {
                  header: 'Unit Price',
                  render: (l) => formatCurrency(l.unit_price),
                },
                {
                  header: 'Tax',
                  render: (l) => `${l.tax_rate}% (${formatCurrency(l.line_tax)})`,
                },
                {
                  header: 'Line Total',
                  render: (l) => (
                    <span className="font-semibold text-white">{formatCurrency(l.line_total)}</span>
                  ),
                },
              ]}
              data={detailQuote.lines || []}
            />

            <div className="flex justify-between items-center bg-slate-950 p-4 rounded-xl border border-slate-800">
              <div className="text-xs text-slate-400 space-y-1">
                <div>Subtotal: {formatCurrency(detailQuote.subtotal)}</div>
                <div>Discount: -{formatCurrency(detailQuote.discount_amount)}</div>
                <div>Tax: {formatCurrency(detailQuote.tax_amount)}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-slate-400">Authoritative Total</div>
                <div className="text-xl font-bold text-emerald-300">
                  {formatCurrency(detailQuote.total)}
                </div>
              </div>
            </div>

            {(detailQuote.status === 'draft' || detailQuote.status === 'sent') && (
              <div className="flex justify-end">
                <button
                  onClick={() => handleConfirmQuote(detailQuote)}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white"
                >
                  Confirm Quotation & Activate Subscription
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

