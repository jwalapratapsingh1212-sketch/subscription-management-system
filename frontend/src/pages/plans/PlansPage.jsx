import React, { useEffect, useState } from 'react';
import { Edit2, Plus } from 'lucide-react';
import { extractErrorMessage, plansApi } from '../../services/api/client';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const PlansPage = () => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [form, setForm] = useState({
    code: '',
    name: '',
    description: '',
    billing_interval: 'monthly',
    minimum_quantity: 1,
    available_from: '',
    available_until: '',
    default_payment_term_days: 14,
    auto_close: false,
    early_close_allowed: true,
    pause_allowed: true,
    resume_allowed: true,
    renewal_allowed: true,
    is_active: true,
  });

  const loadPlans = async () => {
    setLoading(true);
    try {
      const data = await plansApi.list();
      setPlans(data);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  const openCreateModal = () => {
    setEditingPlan(null);
    setForm({
      code: '',
      name: '',
      description: '',
      billing_interval: 'monthly',
      minimum_quantity: 1,
      available_from: '',
      available_until: '',
      default_payment_term_days: 14,
      auto_close: false,
      early_close_allowed: true,
      pause_allowed: true,
      resume_allowed: true,
      renewal_allowed: true,
      is_active: true,
    });
    setModalOpen(true);
  };

  const openEditModal = (plan) => {
    setEditingPlan(plan);
    setForm({
      code: plan.code,
      name: plan.name,
      description: plan.description || '',
      billing_interval: plan.billing_interval,
      minimum_quantity: plan.minimum_quantity,
      available_from: plan.available_from || '',
      available_until: plan.available_until || '',
      default_payment_term_days: plan.default_payment_term_days,
      auto_close: plan.auto_close,
      early_close_allowed: plan.early_close_allowed,
      pause_allowed: plan.pause_allowed,
      resume_allowed: plan.resume_allowed,
      renewal_allowed: plan.renewal_allowed,
      is_active: plan.is_active,
    });
    setModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        code: form.code || undefined,
        minimum_quantity: Number(form.minimum_quantity),
        default_payment_term_days: Number(form.default_payment_term_days),
        available_from: form.available_from || null,
        available_until: form.available_until || null,
      };
      if (editingPlan) {
        await plansApi.update(editingPlan.id, payload);
        setToast({ type: 'success', message: `Plan '${form.name}' updated.` });
      } else {
        await plansApi.create(payload);
        setToast({ type: 'success', message: `Plan '${form.name}' created.` });
      }
      setModalOpen(false);
      loadPlans();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Subscription Plans & Lifecycle Rules</h1>
          <p className="text-xs text-slate-400">
            Configure daily, weekly, monthly, and yearly recurring billing intervals, minimum
            quantities, and lifecycle permissions
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
        >
          <Plus className="w-4 h-4" /> New Plan
        </button>
      </div>

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'Plan',
              render: (r) => (
                <div>
                  <div className="font-semibold text-white">{r.name}</div>
                  <div className="text-xs font-mono text-indigo-300">{r.code}</div>
                </div>
              ),
            },
            {
              header: 'Interval',
              render: (r) => (
                <span className="uppercase font-bold text-xs px-2.5 py-1 rounded-lg bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                  {r.billing_interval}
                </span>
              ),
            },
            {
              header: 'Min Qty',
              render: (r) => <span className="font-semibold text-white">{r.minimum_quantity}</span>,
            },
            {
              header: 'Availability Window',
              render: (r) => (
                <span className="text-xs text-slate-300">
                  {r.available_from || 'Any'} → {r.available_until || 'Evergreen'}
                </span>
              ),
            },
            {
              header: 'Lifecycle Flags',
              render: (r) => (
                <div className="flex flex-wrap gap-1 text-[11px]">
                  {r.pause_allowed && (
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300">
                      Pause
                    </span>
                  )}
                  {r.resume_allowed && (
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300">
                      Resume
                    </span>
                  )}
                  {r.renewal_allowed && (
                    <span className="px-2 py-0.5 rounded bg-sky-500/10 text-sky-300">
                      Renew
                    </span>
                  )}
                  {r.early_close_allowed && (
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300">
                      Early Close
                    </span>
                  )}
                  {r.auto_close && (
                    <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300">
                      Auto-Close
                    </span>
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
                <button
                  onClick={() => openEditModal(r)}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 inline-flex items-center gap-1"
                >
                  <Edit2 className="w-3.5 h-3.5" /> Edit
                </button>
              ),
            },
          ]}
          data={plans}
        />
      )}

      <Modal
        open={modalOpen}
        title={editingPlan ? `Edit Plan: ${editingPlan.name}` : 'Create Subscription Plan'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Plan Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Plan Code</label>
              <input
                type="text"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                placeholder="PLN-MONTHLY-PRO"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Billing Interval *</label>
              <select
                value={form.billing_interval}
                onChange={(e) => setForm({ ...form, billing_interval: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Minimum Quantity *</label>
              <input
                type="number"
                min="1"
                value={form.minimum_quantity}
                onChange={(e) => setForm({ ...form, minimum_quantity: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Payment Terms (Days)</label>
              <input
                type="number"
                min="0"
                value={form.default_payment_term_days}
                onChange={(e) => setForm({ ...form, default_payment_term_days: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Available From</label>
              <input
                type="date"
                value={form.available_from}
                onChange={(e) => setForm({ ...form, available_from: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Available Until</label>
              <input
                type="date"
                value={form.available_until}
                onChange={(e) => setForm({ ...form, available_until: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="text-xs font-semibold text-slate-300 mb-2">
              Allowed Lifecycle Operations
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs text-slate-300">
              {[
                ['pause_allowed', 'Allow Pause'],
                ['resume_allowed', 'Allow Resume'],
                ['renewal_allowed', 'Allow Renewal'],
                ['early_close_allowed', 'Allow Early Close'],
                ['auto_close', 'Auto-Close at Expiry'],
                ['is_active', 'Plan Active'],
              ].map(([field, label]) => (
                <label key={field} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={Boolean(form[field])}
                    onChange={(e) => setForm({ ...form, [field]: e.target.checked })}
                    className="rounded border-slate-700 text-indigo-600"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
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
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Save Plan
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

