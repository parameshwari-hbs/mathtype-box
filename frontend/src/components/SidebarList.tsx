import React, { useState } from 'react';
import { Search, Check, X, Trash2, Tag, HelpCircle, Layers } from 'lucide-react';
import { FormulaDetection, FormulaStatus } from '../types/formula';

interface SidebarListProps {
  formulas: FormulaDetection[];
  selectedFormulaId: string | null;
  onSelectFormula: (id: string, pageNum: number) => void;
  onUpdateStatus: (id: string, status: FormulaStatus) => void;
  onDeleteFormula: (id: string) => void;
  onAcceptAllHighConfidence: () => void;
}

export const SidebarList: React.FC<SidebarListProps> = ({
  formulas,
  selectedFormulaId,
  onSelectFormula,
  onUpdateStatus,
  onDeleteFormula,
  onAcceptAllHighConfidence
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filtered = formulas.filter(f => {
    if (filterStatus !== 'all' && f.status !== filterStatus) return false;
    if (searchTerm && !f.formula_text.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="w-80 h-full glass-panel border-l border-slate-800 flex flex-col z-10">
      {/* Sidebar Header */}
      <div className="p-4 border-b border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-rose-400" />
            <span>Formula Detections ({formulas.length})</span>
          </h2>

          <button
            onClick={onAcceptAllHighConfidence}
            className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 hover:bg-emerald-900/60 px-2 py-1 rounded border border-emerald-800/60 cursor-pointer transition"
            title="Accept all formulas with confidence >= 75%"
          >
            Accept All ≥75%
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search equations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-rose-500"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex space-x-1 text-xs">
          {['all', 'accepted', 'uncertain', 'rejected'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`flex-1 py-1 capitalize rounded text-[11px] font-medium transition cursor-pointer ${
                filterStatus === st
                  ? 'bg-rose-600 text-white font-semibold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-400'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Formula List Scroll Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs">
            No formula detections match your filter.
          </div>
        ) : (
          filtered.map((f) => {
            const isSelected = f.id === selectedFormulaId;

            return (
              <div
                key={f.id}
                onClick={() => onSelectFormula(f.id, f.page_num)}
                className={`p-3 rounded-lg border text-xs cursor-pointer transition space-y-2 ${
                  isSelected
                    ? 'bg-slate-800 border-rose-500 shadow-md shadow-rose-950/50'
                    : 'bg-slate-900/60 hover:bg-slate-800/60 border-slate-800'
                }`}
              >
                {/* Header row */}
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
                    P{f.page_num}
                  </span>

                  <div className="flex items-center space-x-1.5">
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${
                        f.status === 'accepted'
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                          : f.status === 'uncertain'
                          ? 'bg-amber-950/60 text-amber-300 border-amber-800'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {f.status}
                    </span>

                    <span className="text-[10px] text-slate-400 font-mono">
                      {Math.round(f.confidence * 100)}%
                    </span>
                  </div>
                </div>

                {/* Text representation */}
                <div className="font-mono text-slate-200 bg-slate-950 p-2 rounded border border-slate-800/80 truncate text-[11px]">
                  {f.formula_text || '[Mathematical Notation]'}
                </div>

                {/* Footer action bar */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px]">
                  <span className="text-slate-500 font-mono capitalize">
                    {f.detection_method.replace('_', ' ')}
                  </span>

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); onUpdateStatus(f.id, 'accepted'); }}
                      className="p-1 hover:bg-emerald-900/40 text-emerald-400 rounded transition cursor-pointer"
                      title="Accept"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onUpdateStatus(f.id, 'rejected'); }}
                      className="p-1 hover:bg-amber-900/40 text-amber-400 rounded transition cursor-pointer"
                      title="Reject"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDeleteFormula(f.id); }}
                      className="p-1 hover:bg-rose-900/40 text-rose-400 rounded transition cursor-pointer"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
