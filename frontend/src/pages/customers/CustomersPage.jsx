import React, { useEffect, useState } from 'react';
import { Edit2, Plus, Search, UserPlus } from 'lucide-react';
import { customersApi, extractErrorMessage } from '../../services/api/client';
import { formatCurrency } from '../../services/validators';
import { LoadingState, Modal, StatusBadge, ToastBanner } from '../../components/common/UI';
import { DataTable } from '../../components/tables/DataTable';

export const CustomersPage = () => {
  const [customers, setCustomers] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [form, setForm] = useState({
    name: '',
    company_name: '',
    email: '',
    phone: '',
    tax_id: '',
    billing_address: '',
    city: '',
    state: '',
    country: 'US',
    postal_code: '',
    notes: '',
    password: '',
  });

  const loadCustomers = async () => {
    setLoading(true);
    try {
      const res = await customersApi.list({ search: search || undefined, page, page_size: 20 });
      setCustomers(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCustomers();
  }, [page]);

  const openCreateModal = () => {
    setEditingCustomer(null);
    setForm({
      name: '',
      company_name: '',
      email: '',
      phone: '',
      tax_id: '',
      billing_address: '',
      city: '',
      state: '',
      country: 'US',
      postal_code: '',
      notes: '',
      password: '',
    });
    setModalOpen(true);
  };

  const openEditModal = (cust) => {
    setEditingCustomer(cust);
    setForm({
      name: cust.name || '',
      company_name: cust.company_name || '',
      email: cust.email || '',
      phone: cust.phone || '',
      tax_id: cust.tax_id || '',
      billing_address: cust.billing_address || '',
      city: cust.city || '',
      state: cust.state || '',
      country: cust.country || 'US',
      postal_code: cust.postal_code || '',
      notes: cust.notes || '',
      password: '',
    });
    setModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      if (editingCustomer) {
        const { password, ...updatePayload } = form;
        await customersApi.update(editingCustomer.id, updatePayload);
        setToast({ type: 'success', message: `Customer '${form.name}' updated.` });
      } else {
        const createPayload = { ...form };
        if (!createPayload.password) delete createPayload.password;
        await customersApi.create(createPayload);
        setToast({ type: 'success', message: `Customer '${form.name}' created.` });
      }
      setModalOpen(false);
      loadCustomers();
    } catch (err) {
      setToast({ type: 'error', message: extractErrorMessage(err) });
    }
  };

  return (
    <div className="space-y-6">
      <ToastBanner toast={toast} onClose={() => setToast(null)} />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Customer Management</h1>
          <p className="text-xs text-slate-400">
            Manage customer profiles, billing addresses, tax IDs, and receivable balances ({total}{' '}
            total)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setPage(1);
              loadCustomers();
            }}
            className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5"
          >
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, email, company..."
              className="bg-transparent text-xs text-white focus:outline-none w-52"
            />
            <button
              type="submit"
              className="px-2.5 py-1 rounded-lg bg-slate-800 text-xs text-indigo-300 font-semibold"
            >
              Search
            </button>
          </form>

          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg"
          >
            <UserPlus className="w-4 h-4" /> New Customer
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingState />
      ) : (
        <DataTable
          columns={[
            {
              header: 'Customer',
              render: (r) => (
                <div>
                  <div className="font-semibold text-white">{r.name}</div>
                  <div className="text-xs text-slate-400">{r.company_name || 'Individual'}</div>
                </div>
              ),
            },
            {
              header: 'Contact',
              render: (r) => (
                <div>
                  <div className="text-slate-200">{r.email}</div>
                  <div className="text-xs text-slate-500">{r.phone || '—'}</div>
                </div>
              ),
            },
            {
              header: 'Billing Address',
              render: (r) => (
                <div className="text-xs text-slate-300 max-w-xs truncate">
                  {r.billing_address || '—'} {r.city ? `, ${r.city}` : ''}
                </div>
              ),
            },
            {
              header: 'Active Subs',
              render: (r) => (
                <span className="font-semibold text-indigo-300">
                  {r.active_subscriptions_count}
                </span>
              ),
            },
            {
              header: 'Total Billed',
              render: (r) => formatCurrency(r.total_billed),
            },
            {
              header: 'Outstanding',
              render: (r) => (
                <span
                  className={
                    Number(r.outstanding_balance) > 0
                      ? 'font-bold text-rose-400'
                      : 'text-emerald-400'
                  }
                >
                  {formatCurrency(r.outstanding_balance)}
                </span>
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
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200"
                >
                  <Edit2 className="w-3.5 h-3.5" /> Edit
                </button>
              ),
            },
          ]}
          data={customers}
        />
      )}

      <Modal
        open={modalOpen}
        title={editingCustomer ? `Edit Customer: ${editingCustomer.name}` : 'Create New Customer'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Full Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Company Name</label>
              <input
                type="text"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-300 mb-1">Email Address *</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Phone</label>
              <input
                type="text"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-300 mb-1">Billing Street Address</label>
            <input
              type="text"
              value={form.billing_address}
              onChange={(e) => setForm({ ...form, billing_address: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-slate-300 mb-1">City</label>
              <input
                type="text"
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">State / Region</label>
              <input
                type="text"
                value={form.state}
                onChange={(e) => setForm({ ...form, state: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Tax ID / VAT</label>
              <input
                type="text"
                value={form.tax_id}
                onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          {!editingCustomer && (
            <div>
              <label className="block text-xs text-slate-300 mb-1">
                Optional Portal Login Password (leave blank if no login needed yet)
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="e.g. Customer@123"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white"
              />
            </div>
          )}

          <div>
            <label className="block text-xs text-slate-300 mb-1">Account Notes</label>
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
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded-lg text-xs bg-slate-800 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              {editingCustomer ? 'Save Changes' : 'Create Customer'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

