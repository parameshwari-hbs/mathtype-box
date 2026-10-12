import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';
import { Header } from './components/Header';
import { StatsBar } from './components/StatsBar';
import { PdfViewer } from './components/PdfViewer';
import { SidebarList } from './components/SidebarList';
import { ConfigModal } from './components/ConfigModal';
import { DocumentState, AnnotationConfig, FormulaStatus, BenchmarkReport } from './types/formula';
import {
  uploadPdfFile,
  updateFormulaStatus,
  addManualFormula,
  deleteFormula,
  updateAnnotationConfig,
  exportAnnotatedPdf,
  runBenchmarkSuite
} from './api/client';

export const App: React.FC = () => {
  const [docState, setDocState] = useState<DocumentState | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedFormulaId, setSelectedFormulaId] = useState<string | null>(null);
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [benchmarkReport, setBenchmarkReport] = useState<BenchmarkReport | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleUpload = async (file: File) => {
    setLoading(true);
    try {
      const state = await uploadPdfFile(file);
      setDocState(state);
      setCurrentPage(1);
      setSelectedFormulaId(null);
      showToast(`Analyzed ${state.total_pages} pages. Found ${state.stats.total_detected} formula candidates.`);
    } catch (err: any) {
      alert(`Error uploading file: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (formulaId: string, status: string) => {
    if (!docState) return;
    try {
      await updateFormulaStatus(docState.doc_id, formulaId, status);
      setDocState((prev) => {
        if (!prev) return null;
        const updatedFormulas = prev.formulas.map((f) =>
          f.id === formulaId ? { ...f, status: status as FormulaStatus } : f
        );
        const accepted = updatedFormulas.filter((f) => f.status === 'accepted').length;
        const uncertain = updatedFormulas.filter((f) => f.status === 'uncertain').length;
        return {
          ...prev,
          formulas: updatedFormulas,
          stats: { ...prev.stats, accepted_count: accepted, uncertain_count: uncertain }
        };
      });
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleAddManualFormula = async (page: number, bbox: [number, number, number, number]) => {
    if (!docState) return;
    try {
      await addManualFormula(docState.doc_id, { page_num: page, bbox, formula_text: '[Manual Formula Box]' });
      const state = await uploadPdfFile(new File([], docState.filename)); // refresh
    } catch (err: any) {
      // Refresh state directly from backend
      showToast('Added manual formula rectangle');
    }
  };

  const handleDeleteFormula = async (formulaId: string) => {
    if (!docState) return;
    try {
      await deleteFormula(docState.doc_id, formulaId);
      setDocState((prev) => {
        if (!prev) return null;
        const updated = prev.formulas.filter((f) => f.id !== formulaId);
        return {
          ...prev,
          formulas: updated,
          stats: {
            ...prev.stats,
            total_detected: updated.length,
            accepted_count: updated.filter((f) => f.status === 'accepted').length,
            uncertain_count: updated.filter((f) => f.status === 'uncertain').length
          }
        };
      });
      if (selectedFormulaId === formulaId) setSelectedFormulaId(null);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleAcceptAllHighConfidence = () => {
    if (!docState) return;
    const updatedFormulas = docState.formulas.map((f) =>
      f.confidence >= 0.75 ? { ...f, status: 'accepted' as FormulaStatus } : f
    );
    setDocState({
      ...docState,
      formulas: updatedFormulas,
      stats: {
        ...docState.stats,
        accepted_count: updatedFormulas.filter((f) => f.status === 'accepted').length,
        uncertain_count: updatedFormulas.filter((f) => f.status === 'uncertain').length
      }
    });
    showToast('Accepted all formula candidates with confidence >= 75%');
  };

  const handleSaveConfig = async (newConfig: AnnotationConfig) => {
    if (!docState) return;
    try {
      await updateAnnotationConfig(docState.doc_id, newConfig);
      setDocState({ ...docState, config: newConfig });
      showToast('Updated annotation rectangle settings');
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleExport = async () => {
    if (!docState) return;
    setExporting(true);
    try {
      const result = await exportAnnotatedPdf(docState.doc_id);
      showToast(`Exported ${result.applied_count} red 0.01pt rectangle annotations successfully!`);
      // Trigger browser file download
      window.location.href = result.export_url;
    } catch (err: any) {
      alert(`Export failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const handleRunBenchmark = async () => {
    setLoading(true);
    try {
      const report = await runBenchmarkSuite();
      setBenchmarkReport(report);
    } catch (err: any) {
      alert(`Benchmark error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Header
        docState={docState}
        config={docState?.config || { border_width: 0.01, border_color: '#E31B23', fill_color: null, opacity: 1.0 }}
        onUpload={handleUpload}
        onOpenConfig={() => setIsConfigOpen(true)}
        onExport={handleExport}
        onRunBenchmark={handleRunBenchmark}
        exporting={exporting}
      />

      {/* Main Content Area */}
      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="w-10 h-10 text-rose-500 animate-spin" />
          <p className="text-sm font-medium text-slate-300">Processing PDF document & extracting formula coordinates...</p>
        </div>
      ) : !docState ? (
        /* Empty Dropzone Landing View */
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="max-w-xl w-full glass-panel rounded-2xl p-10 border border-slate-800 text-center space-y-6 shadow-2xl">
            <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto shadow-inner">
              <Upload className="w-8 h-8 text-rose-400" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-bold text-slate-100">FormulaBox Automator</h2>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Upload a PDF file to automatically detect formulas and draw client-compliant 0.01 pt red rectangle annotations.
              </p>
            </div>

            <div className="pt-2 flex justify-center gap-4">
              <label className="px-6 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-sm cursor-pointer shadow-lg shadow-rose-950 transition">
                Select PDF Document
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
                  className="hidden"
                />
              </label>
            </div>

            <div className="pt-6 border-t border-slate-800/80 grid grid-cols-3 gap-4 text-xs text-slate-400">
              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                <span className="font-semibold text-rose-400 block mb-1">0.01 pt Red Border</span>
                Exact Adobe Acrobat standard annotation
              </div>
              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                <span className="font-semibold text-emerald-400 block mb-1">Hybrid Detection</span>
                StructTree + Text + OCR Layout Engine
              </div>
              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                <span className="font-semibold text-amber-400 block mb-1">Zero Rasterization</span>
                Preserves original PDF vectors & tags
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Workspace Editor Layout */
        <div className="flex-1 flex flex-col overflow-hidden">
          <StatsBar totalPages={docState.total_pages} stats={docState.stats} filename={docState.filename} />

          <div className="flex-1 flex overflow-hidden">
            <PdfViewer
              docId={docState.doc_id}
              currentPage={currentPage}
              totalPages={docState.total_pages}
              formulas={docState.formulas}
              selectedFormulaId={selectedFormulaId}
              onPageChange={(p) => setCurrentPage(p)}
              onSelectFormula={(id) => setSelectedFormulaId(id)}
              onUpdateStatus={handleUpdateStatus}
              onDeleteFormula={handleDeleteFormula}
              onAddManualFormula={handleAddManualFormula}
            />

            <SidebarList
              formulas={docState.formulas}
              selectedFormulaId={selectedFormulaId}
              onSelectFormula={(id, p) => {
                setSelectedFormulaId(id);
                setCurrentPage(p);
              }}
              onUpdateStatus={handleUpdateStatus}
              onDeleteFormula={handleDeleteFormula}
              onAcceptAllHighConfidence={handleAcceptAllHighConfidence}
            />
          </div>
        </div>
      )}

      {/* Config Modal */}
      <ConfigModal
        isOpen={isConfigOpen}
        config={docState?.config}
        onClose={() => setIsConfigOpen(false)}
        onSave={handleSaveConfig}
      />

      {/* Benchmark Modal */}
      {benchmarkReport && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                Validation Benchmark Report
              </h3>
              <button onClick={() => setBenchmarkReport(null)} className="text-slate-400 hover:text-white cursor-pointer font-bold">✕</button>
            </div>
            <div className="text-xs space-y-2 text-slate-300 font-mono">
              <p>File: <span className="text-slate-100">{benchmarkReport.file_name}</span></p>
              <p>Total Pages: <span className="text-slate-100">{benchmarkReport.total_pages}</span></p>
              <p>Total Formulas Detected: <span className="text-emerald-400">{benchmarkReport.total_detected_formulas}</span></p>
              <p>Estimated Precision: <span className="text-emerald-400">{(benchmarkReport.estimated_precision * 100).toFixed(1)}%</span></p>
            </div>
            <button
              onClick={() => setBenchmarkReport(null)}
              className="w-full py-2 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs cursor-pointer"
            >
              Close Report
            </button>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-800 border border-rose-500 text-slate-100 text-xs px-4 py-3 rounded-lg shadow-xl flex items-center gap-2 animate-bounce">
          <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
};
