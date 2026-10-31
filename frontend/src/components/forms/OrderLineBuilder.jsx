import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { formatCurrency } from '../../services/validators';

export const OrderLineBuilder = ({ lines, setLines, products, taxRules }) => {
  const addLine = () => {
    const firstProd = products[0];
    const defaultTax = taxRules.find((t) => t.is_default) || taxRules[0];
    setLines([
      ...lines,
      {
        product_id: firstProd ? firstProd.id : '',
        variant_id: '',
        tax_rule_id: defaultTax ? defaultTax.id : '',
        quantity: 1,
      },
    ]);
  };

  const updateLine = (idx, field, value) => {
    const next = [...lines];
    next[idx] = { ...next[idx], [field]: value };
    if (field === 'product_id') {
      next[idx].variant_id = '';
    }
    setLines(next);
  };

  const removeLine = (idx) => {
    if (lines.length <= 1) return;
    setLines(lines.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Line Items (Server Calculates Authoritative Totals & Taxes)
        </label>
        <button
          type="button"
          onClick={addLine}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30"
        >
          <Plus className="w-3.5 h-3.5" /> Add Line
        </button>
      </div>

      {lines.map((line, idx) => {
        const selectedProd = products.find((p) => Number(p.id) === Number(line.product_id));
        const variants = selectedProd?.variants?.filter((v) => v.is_active) || [];
        const selectedVar = variants.find((v) => Number(v.id) === Number(line.variant_id));
        const estUnit =
          Number(selectedProd?.sales_price || 0) + Number(selectedVar?.price_extra || 0);

        return (
          <div
            key={idx}
            className="grid grid-cols-12 gap-2 items-end bg-slate-950/70 p-3 rounded-xl border border-slate-800"
          >
            <div className="col-span-4">
              <label className="block text-[11px] text-slate-400 mb-1">Product</label>
              <select
                value={line.product_id}
                onChange={(e) => updateLine(idx, 'product_id', Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-white"
                required
              >
                <option value="">Select product...</option>
                {products
                  .filter((p) => p.is_active)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({formatCurrency(p.sales_price)})
                    </option>
                  ))}
              </select>
            </div>

            <div className="col-span-3">
              <label className="block text-[11px] text-slate-400 mb-1">Variant (Optional)</label>
              <select
                value={line.variant_id || ''}
                onChange={(e) =>
                  updateLine(idx, 'variant_id', e.target.value ? Number(e.target.value) : null)
                }
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-white"
                disabled={variants.length === 0}
              >
                <option value="">Base Product</option>
                {variants.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} (+{formatCurrency(v.price_extra)})
                  </option>
                ))}
              </select>
            </div>

            <div className="col-span-2">
              <label className="block text-[11px] text-slate-400 mb-1">Tax Rule</label>
              <select
                value={line.tax_rule_id || ''}
                onChange={(e) =>
                  updateLine(idx, 'tax_rule_id', e.target.value ? Number(e.target.value) : null)
                }
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-white"
              >
                <option value="">Default Tax</option>
                {taxRules
                  .filter((t) => t.is_active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.code} ({t.rate}%)
                    </option>
                  ))}
              </select>
            </div>

            <div className="col-span-2">
              <label className="block text-[11px] text-slate-400 mb-1">
                Qty (Unit: {formatCurrency(estUnit)})
              </label>
              <input
                type="number"
                min="1"
                value={line.quantity}
                onChange={(e) => updateLine(idx, 'quantity', Math.max(1, Number(e.target.value)))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-white"
                required
              />
            </div>

            <div className="col-span-1 flex justify-end">
              <button
                type="button"
                onClick={() => removeLine(idx)}
                disabled={lines.length <= 1}
                className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 disabled:opacity-30"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

