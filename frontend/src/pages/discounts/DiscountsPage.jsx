import React, { useEffect, useState } from 'react';
import { Percent, Plus, Power, Shield } from 'lucide-react';
import {
  discountsApi,
  extractErrorMessage,
  productsApi,
  taxRulesApi,
} from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const DiscountsPage = () => {
  const [discounts, setDiscounts] = useState([]);
  const [taxRules, setTaxRules] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [discountModalOpen, setDiscountModalOpen] = useState(false);
  const [discountForm, setDiscountForm] = useState({
    name: '',
    code: '',
    discount_type: 'percentage',
    value: '15.00',
    min_purchase_amount: '100.00',
    min_quantity: 1,
    product_id: '',
    applicable_to: 'all',
    start_date: '',
    end_date: '',
    usage_limit: '50',
    is_active: true,
  });

  const [taxModalOpen, setTaxModalOpen] = useState(false);
  const [taxForm, setTaxForm] = useState({
    name: '',
    code: '',
    rate: '10.00',
    region: 'United States',
    category: 'Standard',
    is_default: false,
    is_active: true,
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [dList, tList, pList] = await Promise.all([
        discountsApi.list(),
        taxRulesApi.list(),
        productsApi.list({ is_active: true }),
      ]);
      setDiscounts(dList);
      setTaxRules(tList);
      setProducts(pList);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateDiscount = async (e) => {
    e.preventDefault();
    try {
      await discountsApi.create({
        name: discountForm.name,
        code: discountForm.code.toUpperCase(),
        discount_type: discountForm.discount_type,
        value: discountForm.value,
        min_purchase_amount: discountForm.min_purchase_amount || '0.00',
        min_quantity: Number(discountForm.min_quantity || 0),
        product_id: discountForm.product_id ? Number(discountForm.product_id) : null,
        applicable_to: discountForm.product_id ? 'product' : discountForm.applicable_to,
        start_date: discountForm.start_date || null,
        end_date: discountForm.end_date || null,
        usage_limit: discountForm.usage_limit ? Number(discountForm.usage_limit) : null,
        is_active: discountForm.is_active,
      });
      setToast({
        type: 'success',
        message: `Discount '${discountForm.code.toUpperCase()}' created.`,
      });
      setDiscountModalOpen(false);
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleToggleDiscount = async (d) => {
    try {
      await discountsApi.update(d.id, { is_active: !d.is_active });
      setToast({
        type: 'success',
        message: `Discount '${d.code}' ${!d.is_active ? 'activated' : 'deactivated'}.`,
      });
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleCreateTaxRule = async (e) => {
    e.preventDefault();
    try {
      await taxRulesApi.create({
        ...taxForm,
        code: taxForm.code || undefined,
      });
      setToast({ type: 'success', message: `Tax rule '${taxForm.name}' created.` });
      setTaxModalOpen(false);
      loadData();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-8">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      {/* Discounts Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Discounts & Tax Rules Engine</h1>
            <p className="text-xs text-slate-400">
              Manage fixed & percentage promotions, eligibility minimums, usage limits, and
              configurable tax rules
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setTaxModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700"
            >
              <Shield className="w-4 h-4" /> + New Tax Rule
            </button>
            <button
              onClick={() => setDiscountModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
            >
              <Plus className="w-4 h-4" /> + New Discount Rule
            </button>
          </div>
        </div>

        {loading ? (
          <LoadingState />
        ) : (
          <DataTable
            columns={[
              {
                header: 'Promo Code & Name',
                render: (r) => (
                  <div>
                    <div className="font-mono font-bold text-indigo-300">{r.code}</div>
                    <div className="text-xs text-slate-300">{r.name}</div>
                  </div>
                ),
              },
              {
                header: 'Type & Value',
                render: (r) => (
                  <span className="font-bold text-emerald-300">
                    {r.discount_type === 'percentage'
                      ? `${r.value}% OFF`
                      : `${formatCurrency(r.value)} OFF`}
                  </span>
                ),
              },
              {
                header: 'Eligibility Minimums',
                render: (r) => (
                  <div className="text-xs text-slate-300">
                    <div>Min Purchase: {formatCurrency(r.min_purchase_amount)}</div>
                    <div>Min Qty: {r.min_quantity}</div>
                  </div>
                ),
              },
              {
                header: 'Validity Window',
                render: (r) => (
                  <span className="text-xs text-slate-400">
                    {r.start_date || 'Immediate'} → {r.end_date || 'No Expiry'}
                  </span>
                ),
              },
              {
                header: 'Usage Tracking',
                render: (r) => (
                  <span className="text-xs font-semibold text-white">
                    {r.usage_count} / {r.usage_limit ?? '∞'} used
                  </span>
                ),
              },
              {
                header: 'Status',
                render: (r) => <StatusBadge status={r.is_active ? 'active' : 'closed'} />,
              },
              {
                header: 'Action',
                render: (r) => (
                  <button
                    onClick={() => handleToggleDiscount(r)}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-amber-300 inline-flex items-center gap-1"
                  >
                    <Power className="w-3 h-3" /> {r.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                ),
              },
            ]}
            data={discounts}
          />
        )}
      </div>

      {/* Configurable Tax Rules Section */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-white">Configurable Tax Rules</h2>
        <DataTable
          columns={[
            {
              header: 'Code',
              render: (r) => <span className="font-mono text-indigo-300">{r.code}</span>,
            },
            { header: 'Tax Rule Name', accessor: 'name' },
            {
              header: 'Rate (%)',
              render: (r) => <span className="font-bold text-white">{r.rate}%</span>,
            },
            { header: 'Region', accessor: 'region' },
            { header: 'Category', accessor: 'category' },
            {
              header: 'Default',
              render: (r) =>
                r.is_default ? (
                  <span className="text-xs font-semibold text-emerald-400">Default Rule</span>
                ) : (
                  <span className="text-xs text-slate-500">—</span>
                ),
            },
            {
              header: 'Status',
              render: (r) => <StatusBadge status={r.is_active ? 'active' : 'closed'} />,
            },
          ]}
          data={taxRules}
        />
      </div>

      {/* Create Discount Modal */}
      <Modal
        open={discountModalOpen}
        title="Create Promotional Discount Rule"
        onClose={() => setDiscountModalOpen(false)}
      >
        <form onSubmit={handleCreateDiscount} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Promotion Name *</label>
              <input
                type="text"
                value={discountForm.name}
                onChange={(e) => setDiscountForm({ ...discountForm, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Promo Code *</label>
              <input
                type="text"
                value={discountForm.code}
                onChange={(e) => setDiscountForm({ ...discountForm, code: e.target.value })}
                placeholder="SPRING20"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono uppercase"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Discount Type</label>
              <select
                value={discountForm.discount_type}
                onChange={(e) =>
                  setDiscountForm({ ...discountForm, discount_type: e.target.value })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              >
                <option value="percentage">Percentage (%)</option>
                <option value="fixed">Fixed Amount ($)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Value *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={discountForm.value}
                onChange={(e) => setDiscountForm({ ...discountForm, value: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Usage Limit</label>
              <input
                type="number"
                min="1"
                value={discountForm.usage_limit}
                onChange={(e) =>
                  setDiscountForm({ ...discountForm, usage_limit: e.target.value })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Min Purchase ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={discountForm.min_purchase_amount}
                onChange={(e) =>
                  setDiscountForm({ ...discountForm, min_purchase_amount: e.target.value })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Min Quantity</label>
              <input
                type="number"
                min="0"
                value={discountForm.min_quantity}
                onChange={(e) =>
                  setDiscountForm({ ...discountForm, min_quantity: e.target.value })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Product Scope</label>
              <select
                value={discountForm.product_id}
                onChange={(e) =>
                  setDiscountForm({ ...discountForm, product_id: e.target.value })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              >
                <option value="">All Products / Subscription-Wide</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    Only: {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Start Date</label>
              <input
                type="date"
                value={discountForm.start_date}
                onChange={(e) => setDiscountForm({ ...discountForm, start_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Expiry Date</label>
              <input
                type="date"
                value={discountForm.end_date}
                onChange={(e) => setDiscountForm({ ...discountForm, end_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setDiscountModalOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Save Discount Rule
            </button>
          </div>
        </form>
      </Modal>

      {/* Create Tax Rule Modal */}
      <Modal
        open={taxModalOpen}
        title="Create Configurable Tax Rule"
        onClose={() => setTaxModalOpen(false)}
        maxWidth="max-w-md"
      >
        <form onSubmit={handleCreateTaxRule} className="space-y-4">
          <div>
            <label className="block text-xs text-slate-300 mb-1">Tax Rule Name *</label>
            <input
              type="text"
              value={taxForm.name}
              onChange={(e) => setTaxForm({ ...taxForm, name: e.target.value })}
              placeholder="California Digital SaaS Tax"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Tax Code</label>
              <input
                type="text"
                value={taxForm.code}
                onChange={(e) => setTaxForm({ ...taxForm, code: e.target.value })}
                placeholder="TAX-CA-825"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Tax Rate (%) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                value={taxForm.rate}
                onChange={(e) => setTaxForm({ ...taxForm, rate: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Region</label>
              <input
                type="text"
                value={taxForm.region}
                onChange={(e) => setTaxForm({ ...taxForm, region: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Category</label>
              <input
                type="text"
                value={taxForm.category}
                onChange={(e) => setTaxForm({ ...taxForm, category: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={taxForm.is_default}
              onChange={(e) => setTaxForm({ ...taxForm, is_default: e.target.checked })}
            />
            <span>Set as default tax rule for new orders</span>
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setTaxModalOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Create Tax Rule
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

