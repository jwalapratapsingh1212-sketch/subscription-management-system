import React from 'react';
import { AlertCircle, CheckCircle2, Info, Loader2, X } from 'lucide-react';

const BADGE_STYLES = {
  active: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  paid: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  succeeded: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  confirmed: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  sent: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  quotation: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  partially_paid: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  paused: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  unpaid: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  draft: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  overdue: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  past_due: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  expired: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  closed: 'bg-zinc-600/20 text-zinc-400 border-zinc-600/30',
  cancelled: 'bg-zinc-600/20 text-zinc-400 border-zinc-600/30',
  admin: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  staff: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  customer: 'bg-teal-500/20 text-teal-300 border-teal-500/30',
};

export const StatusBadge = ({ status }) => {
  const key = String(status || 'draft').toLowerCase();
  const cls = BADGE_STYLES[key] || 'bg-slate-700/40 text-slate-300 border-slate-600';
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider ${cls}`}
    >
      {String(status || '').replace(/_/g, ' ')}
    </span>
  );
};

export const MetricCard = ({ title, value, subtitle, icon: Icon, accent = 'indigo' }) => {
  const accentMap = {
    indigo: 'from-indigo-500/20 to-indigo-600/5 border-indigo-500/30 text-indigo-400',
    emerald: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/30 text-emerald-400',
    amber: 'from-amber-500/20 to-amber-600/5 border-amber-500/30 text-amber-400',
    rose: 'from-rose-500/20 to-rose-600/5 border-rose-500/30 text-rose-400',
    cyan: 'from-cyan-500/20 to-cyan-600/5 border-cyan-500/30 text-cyan-400',
  };
  const colors = accentMap[accent] || accentMap.indigo;

  return (
    <div className={`bg-gradient-to-br ${colors} border rounded-xl p-5 shadow-lg`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && <Icon className="w-5 h-5 opacity-80" />}
      </div>
      <div className="mt-2 text-2xl font-bold text-white tracking-tight">{value}</div>
      {subtitle && <div className="mt-1 text-xs text-slate-400">{subtitle}</div>}
    </div>
  );
};

export const ToastBanner = ({ toast, onClose }) => {
  if (!toast) return null;
  const isError = toast.type === 'error';
  return (
    <div
      className={`fixed bottom-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-2xl max-w-md ${
        isError
          ? 'bg-rose-950/95 border-rose-500/40 text-rose-200'
          : 'bg-emerald-950/95 border-emerald-500/40 text-emerald-200'
      }`}
    >
      {isError ? (
        <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
      ) : (
        <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
      )}
      <div className="text-sm font-medium flex-1">{toast.message}</div>
      <button
        onClick={onClose}
        className="text-slate-400 hover:text-white p-1 rounded"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export const Modal = ({ open, title, onClose, children, maxWidth = 'max-w-2xl' }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div
        className={`bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl w-full ${maxWidth} overflow-hidden`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 max-h-[82vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
};

export const ConfirmDialog = ({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  danger = false,
  onConfirm,
  onCancel,
}) => {
  if (!open) return null;
  return (
    <Modal open={open} title={title} onClose={onCancel} maxWidth="max-w-md">
      <p className="text-sm text-slate-300 leading-relaxed">{message}</p>
      <div className="mt-6 flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-800 text-slate-300 hover:bg-slate-700"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className={`px-4 py-2 rounded-lg text-sm font-semibold text-white ${
            danger ? 'bg-rose-600 hover:bg-rose-500' : 'bg-indigo-600 hover:bg-indigo-500'
          }`}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
};

export const LoadingState = ({ label = 'Loading data...' }) => (
  <div className="flex flex-col items-center justify-center py-16 text-slate-400">
    <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
    <span className="text-sm">{label}</span>
  </div>
);

export const EmptyState = ({ title, description, action }) => (
  <div className="flex flex-col items-center justify-center py-12 px-4 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/40">
    <Info className="w-8 h-8 text-slate-500 mb-2" />
    <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
    {description && <p className="text-xs text-slate-400 mt-1 max-w-md">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

