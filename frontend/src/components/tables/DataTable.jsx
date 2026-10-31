import React from 'react';
import { EmptyState } from '../common/UI';

export const DataTable = ({ columns, data, keyField = 'id', emptyTitle = 'No records found' }) => {
  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} />;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-slate-800 bg-slate-900/90 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {columns.map((col, idx) => (
              <th key={idx} className={`px-4 py-3.5 ${col.className || ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/70 text-sm">
          {data.map((row, rIdx) => (
            <tr
              key={row[keyField] ?? rIdx}
              className="hover:bg-slate-800/40 transition-colors"
            >
              {columns.map((col, cIdx) => (
                <td key={cIdx} className={`px-4 py-3.5 ${col.cellClassName || ''}`}>
                  {col.render ? col.render(row) : row[col.accessor]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

