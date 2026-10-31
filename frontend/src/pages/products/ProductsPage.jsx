import React, { useEffect, useState } from 'react';
import { Edit2, Layers, Plus, Power } from 'lucide-react';
import { extractErrorMessage, productsApi } from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [productModalOpen, setProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [form, setForm] = useState({
    sku: '',
    name: '',
    product_type: 'software',
    sales_price: '100.00',
    cost_price: '20.00',
    notes: '',
    is_active: true,
  });

  const [variantModalProduct, setVariantModalProduct] = useState(null);
  const [variantForm, setVariantForm] = useState({
    name: '',
    sku: '',
    attribute_name: 'Tier',
    attribute_value: '',
    price_extra: '50.00',
  });

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await productsApi.list();
      setProducts(data);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const openCreateModal = () => {
    setEditingProduct(null);
    setForm({
      sku: '',
      name: '',
      product_type: 'software',
      sales_price: '199.00',
      cost_price: '35.00',
      notes: '',
      is_active: true,
    });
    setProductModalOpen(true);
  };

  const openEditModal = (prod) => {
    setEditingProduct(prod);
    setForm({
      sku: prod.sku,
      name: prod.name,
      product_type: prod.product_type,
      sales_price: String(prod.sales_price),
      cost_price: String(prod.cost_price),
      notes: prod.notes || '',
      is_active: prod.is_active,
    });
    setProductModalOpen(true);
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        sku: form.sku || undefined,
      };
      if (editingProduct) {
        await productsApi.update(editingProduct.id, payload);
        setToast({ type: 'success', message: `Product '${form.name}' updated.` });
      } else {
        await productsApi.create(payload);
        setToast({ type: 'success', message: `Product '${form.name}' created.` });
      }
      setProductModalOpen(false);
      loadProducts();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleToggleActive = async (prod) => {
    try {
      await productsApi.update(prod.id, { is_active: !prod.is_active });
      setToast({
        type: 'success',
        message: `Product '${prod.name}' ${!prod.is_active ? 'activated' : 'deactivated'}.`,
      });
      loadProducts();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  const handleAddVariant = async (e) => {
    e.preventDefault();
    if (!variantModalProduct) return;
    try {
      await productsApi.createVariant(variantModalProduct.id, variantForm);
      setToast({
        type: 'success',
        message: `Added variant '${variantForm.name}' to ${variantModalProduct.name}.`,
      });
      setVariantForm({
        name: '',
        sku: '',
        attribute_name: 'Tier',
        attribute_value: '',
        price_extra: '50.00',
      });
      setVariantModalProduct(null);
      loadProducts();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Product Catalog & Variant Pricing</h1>
          <p className="text-xs text-slate-400">
            Configure sellable products, sales/cost prices, variants with price adjustments, and
            active status
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
        >
          <Plus className="w-4 h-4" /> New Product
        </button>
      </div>

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'SKU & Name',
              render: (r) => (
                <div>
                  <div className="font-semibold text-white">{r.name}</div>
                  <div className="text-xs font-mono text-indigo-300">{r.sku}</div>
                </div>
              ),
            },
            {
              header: 'Type',
              render: (r) => <span className="capitalize text-slate-300">{r.product_type}</span>,
            },
            {
              header: 'Sales Price',
              render: (r) => (
                <span className="font-bold text-emerald-300">{formatCurrency(r.sales_price)}</span>
              ),
            },
            {
              header: 'Cost Price',
              render: (r) => <span className="text-slate-400">{formatCurrency(r.cost_price)}</span>,
            },
            {
              header: 'Variants (+Extra Price)',
              render: (r) => (
                <div className="flex flex-wrap gap-1.5">
                  {(r.variants || []).length === 0 ? (
                    <span className="text-xs text-slate-500">Base only</span>
                  ) : (
                    r.variants.map((v) => (
                      <span
                        key={v.id}
                        className="px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-xs text-slate-200"
                      >
                        {v.name} (+{formatCurrency(v.price_extra)})
                      </span>
                    ))
                  )}
                </div>
              ),
            },
            {
              header: 'Status',
              render: (r) => <StatusBadge status={r.is_active ? 'active' : 'closed'} />,
            },
            {
              header: 'Actions',
              render: (r) => (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEditModal(r)}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 inline-flex items-center gap-1"
                  >
                    <Edit2 className="w-3 h-3" /> Edit
                  </button>
                  <button
                    onClick={() => setVariantModalProduct(r)}
                    className="px-2.5 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs text-indigo-300 inline-flex items-center gap-1"
                  >
                    <Layers className="w-3 h-3" /> +Variant
                  </button>
                  <button
                    onClick={() => handleToggleActive(r)}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-amber-300 inline-flex items-center gap-1"
                  >
                    <Power className="w-3 h-3" /> {r.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </div>
              ),
            },
          ]}
          data={products}
        />
      )}

      {/* Product Create/Edit Modal */}
      <Modal
        open={productModalOpen}
        title={editingProduct ? `Edit Product: ${editingProduct.name}` : 'Create Product'}
        onClose={() => setProductModalOpen(false)}
      >
        <form onSubmit={handleSaveProduct} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Product Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">SKU (auto-generated if blank)</label>
              <input
                type="text"
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
                placeholder="PRD-CLOUD-01"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Product Type</label>
              <select
                value={form.product_type}
                onChange={(e) => setForm({ ...form, product_type: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              >
                <option value="software">Software</option>
                <option value="service">Service</option>
                <option value="digital">Digital</option>
                <option value="consumable">Consumable</option>
                <option value="hardware">Hardware</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Sales Price ($) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.sales_price}
                onChange={(e) => setForm({ ...form, sales_price: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Cost Price ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.cost_price}
                onChange={(e) => setForm({ ...form, cost_price: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-300 mb-1">Product Notes / Description</label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setProductModalOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Save Product
            </button>
          </div>
        </form>
      </Modal>

      {/* Add Variant Modal */}
      <Modal
        open={Boolean(variantModalProduct)}
        title={`Add Variant to: ${variantModalProduct?.name}`}
        onClose={() => setVariantModalProduct(null)}
        maxWidth="max-w-md"
      >
        <form onSubmit={handleAddVariant} className="space-y-4">
          <div>
            <label className="block text-xs text-slate-300 mb-1">Variant Name *</label>
            <input
              type="text"
              value={variantForm.name}
              onChange={(e) => setVariantForm({ ...variantForm, name: e.target.value })}
              placeholder="e.g. Enterprise 24/7 SLA Tier"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Attribute Name</label>
              <input
                type="text"
                value={variantForm.attribute_name}
                onChange={(e) => setVariantForm({ ...variantForm, attribute_name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Attribute Value</label>
              <input
                type="text"
                value={variantForm.attribute_value}
                onChange={(e) =>
                  setVariantForm({ ...variantForm, attribute_value: e.target.value })
                }
                placeholder="Premium"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">
              Additional Variant Price ($ Extra over Base Price) *
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={variantForm.price_extra}
              onChange={(e) => setVariantForm({ ...variantForm, price_extra: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              required
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setVariantModalProduct(null)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Add Variant
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

