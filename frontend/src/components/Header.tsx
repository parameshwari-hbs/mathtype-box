import React, { useRef } from 'react';
import { FileText, Download, Sliders, Play, Upload, ShieldCheck } from 'lucide-react';
import { DocumentState, AnnotationConfig } from '../types/formula';

interface HeaderProps {
  docState: DocumentState | null;
  config: AnnotationConfig;
  onUpload: (file: File) => void;
  onOpenConfig: () => void;
  onExport: () => void;
  onRunBenchmark: () => void;
  exporting: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  docState,
  config,
  onUpload,
  onOpenConfig,
  onExport,
  onRunBenchmark,
  exporting
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  return (
    <header className="h-16 px-6 glass-panel flex items-center justify-between z-20 shadow-lg border-b border-slate-800">
      {/* Brand Title */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-600 to-amber-500 flex items-center justify-center shadow-md shadow-rose-900/30">
          <FileText className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-lg text-slate-100 tracking-tight flex items-center gap-2">
            FormulaBox Automator
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
              0.01pt Red Rectangle Standard
            </span>
          </h1>
          <p className="text-xs text-slate-400">PDF Math Annotation & Precision Layout Engine</p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-3">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="application/pdf"
          className="hidden"
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition border border-slate-700 shadow-sm cursor-pointer"
        >
          <Upload className="w-4 h-4 text-slate-400" />
          <span>{docState ? 'Change PDF' : 'Upload PDF'}</span>
        </button>

        {/* Validation Benchmark - Hidden from UI per user preference */}
        <button
          onClick={onRunBenchmark}
          className="hidden px-3.5 py-2 rounded-lg bg-indigo-900/40 hover:bg-indigo-900/60 text-indigo-300 text-sm font-medium items-center gap-2 transition border border-indigo-700/50 shadow-sm cursor-pointer"
          title="Run accuracy benchmark validation suite"
        >
          <Play className="w-4 h-4 text-indigo-400" />
          <span>Validation Benchmark</span>
        </button>

        <button
          onClick={onOpenConfig}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 cursor-pointer"
          title="Configure Rectangle Settings"
        >
          <Sliders className="w-4.5 h-4.5" />
        </button>

        {docState && (
          <button
            onClick={onExport}
            disabled={exporting}
            className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-sm flex items-center gap-2 shadow-lg shadow-rose-900/40 transition cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{exporting ? 'Generating PDF...' : 'Export Annotated PDF'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
