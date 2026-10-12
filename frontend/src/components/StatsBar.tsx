import React from 'react';
import { Layers, CheckCircle2, AlertTriangle, Square, FileText } from 'lucide-react';
import { DocumentStats } from '../types/formula';

interface StatsBarProps {
  totalPages: number;
  stats: DocumentStats;
  filename: string;
}

export const StatsBar: React.FC<StatsBarProps> = ({ totalPages, stats, filename }) => {
  return (
    <div className="h-12 bg-slate-900/90 border-b border-slate-800 px-6 flex items-center justify-between text-xs text-slate-300">
      <div className="flex items-center space-x-2 font-mono text-slate-400 truncate max-w-xs">
        <FileText className="w-3.5 h-3.5 text-rose-400 shrink-0" />
        <span className="truncate">{filename}</span>
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-1.5">
          <Layers className="w-3.5 h-3.5 text-slate-400" />
          <span>Pages:</span>
          <span className="font-semibold text-slate-100">{totalPages}</span>
        </div>

        <div className="flex items-center space-x-1.5">
          <Square className="w-3.5 h-3.5 text-blue-400" />
          <span>Detected Formulas:</span>
          <span className="font-semibold text-blue-300">{stats.total_detected}</span>
        </div>

        <div className="flex items-center space-x-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Accepted / Ready:</span>
          <span className="font-semibold text-emerald-300">{stats.accepted_count}</span>
        </div>

        <div className="flex items-center space-x-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span>Pending Review:</span>
          <span className="font-semibold text-amber-300">{stats.uncertain_count}</span>
        </div>
      </div>
    </div>
  );
};
