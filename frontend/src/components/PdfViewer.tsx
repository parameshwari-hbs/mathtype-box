import React, { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Eye, EyeOff, PlusCircle, Check, X, Trash2, CheckCircle2 } from 'lucide-react';
import { FormulaDetection } from '../types/formula';
import { getPageImageUrl } from '../api/client';

interface PdfViewerProps {
  docId: string;
  currentPage: number;
  totalPages: number;
  formulas: FormulaDetection[];
  selectedFormulaId: string | null;
  onPageChange: (page: number) => void;
  onSelectFormula: (id: string | null) => void;
  onUpdateStatus: (id: string, status: string) => void;
  onDeleteFormula: (id: string) => void;
  onAddManualFormula: (page: number, bbox: [number, number, number, number]) => void;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({
  docId,
  currentPage,
  totalPages,
  formulas,
  selectedFormulaId,
  onPageChange,
  onSelectFormula,
  onUpdateStatus,
  onDeleteFormula,
  onAddManualFormula
}) => {
  const [zoom, setZoom] = useState<number>(1.5);
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [continuousScroll, setContinuousScroll] = useState<boolean>(true);
  const [drawMode, setDrawMode] = useState<boolean>(false);
  const [showAnnotatedOnly, setShowAnnotatedOnly] = useState<boolean>(false);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [activeDrawPage, setActiveDrawPage] = useState<number | null>(null);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<{ [key: number]: HTMLDivElement | null }>({});
  const isProgrammaticScrollRef = useRef<boolean>(false);

  // Group formulas by page for O(1) page lookup
  const formulasByPage = React.useMemo(() => {
    const map: { [key: number]: FormulaDetection[] } = {};
    for (let p = 1; p <= totalPages; p++) {
      map[p] = [];
    }
    for (const f of formulas) {
      if (!map[f.page_num]) {
        map[f.page_num] = [];
      }
      if (showAnnotatedOnly) {
        // Show only manual boxes, not existing tool-detected boxes
        if (f.detection_method === 'manual') {
          map[f.page_num].push(f);
        }
      } else {
        map[f.page_num].push(f);
      }
    }
    return map;
  }, [formulas, totalPages, showAnnotatedOnly]);

  // Track scroll position to update current page indicator smoothly
  const handleScroll = () => {
    if (!continuousScroll || !containerRef.current || isProgrammaticScrollRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const triggerY = containerRect.top + containerRect.height * 0.35;

    let closestPage = currentPage;
    let minDistance = Infinity;

    for (let p = 1; p <= totalPages; p++) {
      const el = pageRefs.current[p];
      if (el) {
        const rect = el.getBoundingClientRect();
        const dist = Math.abs(rect.top - triggerY);
        if (dist < minDistance) {
          minDistance = dist;
          closestPage = p;
        }
      }
    }

    if (closestPage !== currentPage) {
      onPageChange(closestPage);
    }
  };

  // Scroll smoothly when user navigates page via toolbar or sidebar
  useEffect(() => {
    const el = pageRefs.current[currentPage];
    if (el && containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      const isVisible =
        elRect.top >= containerRect.top - 80 &&
        elRect.bottom <= containerRect.bottom + 80;

      if (!isVisible) {
        isProgrammaticScrollRef.current = true;
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        const timer = setTimeout(() => {
          isProgrammaticScrollRef.current = false;
        }, 700);
        return () => clearTimeout(timer);
      }
    }
    return undefined;
  }, [currentPage]);

  // Handle manual drawing on canvas for any page
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>, pageNum: number) => {
    if (!drawMode) return;
    const pageEl = pageRefs.current[pageNum];
    if (!pageEl) return;
    const rect = pageEl.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    setActiveDrawPage(pageNum);
    setDrawStart({ x, y });
    setDrawCurrent({ x, y });
    setIsDrawing(true);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !drawMode || activeDrawPage === null) return;
    const pageEl = pageRefs.current[activeDrawPage];
    if (!pageEl) return;
    const rect = pageEl.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    setDrawCurrent({ x, y });
  };

  const handleMouseUp = () => {
    if (!isDrawing || !drawStart || !drawCurrent || activeDrawPage === null) return;
    setIsDrawing(false);

    const x0 = Math.min(drawStart.x, drawCurrent.x);
    const y0 = Math.min(drawStart.y, drawCurrent.y);
    const x1 = Math.max(drawStart.x, drawCurrent.x);
    const y1 = Math.max(drawStart.y, drawCurrent.y);

    // Only add if box has reasonable width and height
    if (x1 - x0 > 8 && y1 - y0 > 8) {
      setShowBoxes(true);
      onAddManualFormula(activeDrawPage, [
        Math.round(x0 * 100) / 100,
        Math.round(y0 * 100) / 100,
        Math.round(x1 * 100) / 100,
        Math.round(y1 * 100) / 100
      ]);
    }

    setDrawStart(null);
    setDrawCurrent(null);
    setActiveDrawPage(null);
  };

  const scrollToPage = (targetPage: number) => {
    const clamped = Math.max(1, Math.min(totalPages, targetPage));
    onPageChange(clamped);
    const el = pageRefs.current[clamped];
    if (el) {
      isProgrammaticScrollRef.current = true;
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setTimeout(() => {
        isProgrammaticScrollRef.current = false;
      }, 700);
    }
  };

  const pageList = continuousScroll
    ? Array.from({ length: totalPages }, (_, i) => i + 1)
    : [currentPage];

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden relative">
      {/* Control Toolbar */}
      <div className="h-12 bg-slate-900 px-6 flex items-center justify-between border-b border-slate-800 z-10 shrink-0">
        {/* Page Navigation & Scroll Tick Box */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => scrollToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 cursor-pointer"
              title="Previous Page"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            <span className="text-sm font-medium text-slate-300">
              Page <span className="text-slate-100 font-bold">{currentPage}</span> of {totalPages}
            </span>

            <button
              onClick={() => scrollToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 cursor-pointer"
              title="Next Page"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          <div className="h-5 w-px bg-slate-800" />

          {/* Scroll Tick Box */}
          <label className="flex items-center space-x-2 cursor-pointer select-none px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/70 transition shadow-sm">
            <input
              type="checkbox"
              id="scroll-pages-checkbox"
              checked={continuousScroll}
              onChange={(e) => setContinuousScroll(e.target.checked)}
              className="w-4 h-4 rounded text-rose-600 focus:ring-rose-500 bg-slate-900 border-slate-600 cursor-pointer accent-rose-600"
            />
            <span className="text-xs font-semibold text-slate-200">Scroll Pages</span>
          </label>
        </div>

        {/* View & Draw Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowBoxes(!showBoxes)}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
              showBoxes ? 'bg-indigo-900/40 text-indigo-300 border border-indigo-700/50' : 'bg-slate-800 text-slate-400'
            }`}
          >
            {showBoxes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>{showBoxes ? 'Boxes Visible' : 'Boxes Hidden'}</span>
          </button>

          {/* Checkbox for Show Annotated Box Alone */}
          <label className={`flex items-center space-x-2 cursor-pointer select-none px-2.5 py-1.5 rounded text-xs font-semibold border transition shadow-sm ${
            showAnnotatedOnly
              ? 'bg-emerald-950/80 text-emerald-200 border-emerald-600 shadow-emerald-950/50'
              : 'bg-slate-800/80 hover:bg-slate-800 text-slate-300 border-slate-700/70'
          }`}>
            <input
              type="checkbox"
              id="show-annotated-alone-checkbox"
              checked={showAnnotatedOnly}
              onChange={(e) => {
                setShowAnnotatedOnly(e.target.checked);
                if (e.target.checked) setShowBoxes(true);
              }}
              className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 bg-slate-900 border-slate-600 cursor-pointer accent-emerald-600"
            />
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Show Annotated Box (Manual Only)</span>
          </label>

          {/* Checkbox for Add Manual Box */}
          <label className={`flex items-center space-x-2 cursor-pointer select-none px-3 py-1.5 rounded text-xs font-semibold border transition shadow-sm ${
            drawMode
              ? 'bg-rose-950/80 text-rose-200 border-rose-600 shadow-rose-950/50'
              : 'bg-slate-800/80 hover:bg-slate-800 text-slate-300 border-slate-700/70'
          }`}>
            <input
              type="checkbox"
              id="draw-manual-box-checkbox"
              checked={drawMode}
              onChange={(e) => {
                setDrawMode(e.target.checked);
                if (e.target.checked) {
                  setShowBoxes(true);
                  onSelectFormula(null);
                }
              }}
              className="w-4 h-4 rounded text-rose-600 focus:ring-rose-500 bg-slate-900 border-slate-600 cursor-pointer accent-rose-600"
            />
            <PlusCircle className="w-3.5 h-3.5 text-rose-400" />
            <span>{drawMode ? 'Draw Manual Box Active' : 'Add Manual Box'}</span>
          </label>

          {/* Zoom Buttons */}
          <div className="flex items-center bg-slate-800 rounded border border-slate-700 p-0.5">
            <button
              onClick={() => setZoom(Math.max(0.75, Math.round((zoom - 0.25) * 100) / 100))}
              className="p-1 hover:bg-slate-700 rounded text-slate-300 cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono px-2 text-slate-300">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom(Math.min(2.5, Math.round((zoom + 0.25) * 100) / 100))}
              className="p-1 hover:bg-slate-700 rounded text-slate-300 cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Continuous Scroll Render Area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-auto p-8 flex flex-col items-center gap-10 relative select-none scroll-smooth"
      >
        {pageList.map((pageNum) => {
          const pageFormulas = formulasByPage[pageNum] || [];
          const isCurrentActivePage = pageNum === currentPage;
          const selectedFormulaOnThisPage = selectedFormulaId
            ? pageFormulas.find((f) => f.id === selectedFormulaId)
            : null;

          return (
            <div
              key={pageNum}
              id={`page-container-${pageNum}`}
              ref={(el) => { pageRefs.current[pageNum] = el; }}
              className={`relative shadow-2xl rounded border bg-white group transition-shadow ${
                drawMode ? 'cursor-crosshair ring-2 ring-rose-500/40' : ''
              } ${
                isCurrentActivePage ? 'border-indigo-500/50 shadow-indigo-950/30' : 'border-slate-800 shadow-black/50'
              }`}
              style={{ width: `${612 * zoom}px` }}
              onMouseDown={(e) => handleMouseDown(e, pageNum)}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
            >
              {/* Subtle Page Indicator Label */}
              <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded bg-slate-900/80 backdrop-blur-sm text-[10px] font-mono text-slate-300 border border-slate-700/60 pointer-events-none opacity-50 group-hover:opacity-100 transition">
                Page {pageNum}
              </div>

              {/* Floating action popover for selected formula */}
              {selectedFormulaOnThisPage && (
                <div
                  className="absolute z-30 flex items-center space-x-1.5 bg-slate-900/95 text-white rounded-md px-2 py-1 shadow-2xl border border-slate-700 text-xs pointer-events-auto backdrop-blur-sm"
                  style={{
                    left: `${Math.max(4, selectedFormulaOnThisPage.bbox[0] * zoom)}px`,
                    top: `${Math.max(4, (selectedFormulaOnThisPage.bbox[1] * zoom) - 38)}px`,
                  }}
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* On manual boxes OR uncertain boxes: show Accept (✓), Reject (✕), Delete (🗑) */}
                  {selectedFormulaOnThisPage.detection_method === 'manual' || selectedFormulaOnThisPage.status !== 'accepted' ? (
                    <>
                      <button
                        type="button"
                        onMouseDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          onUpdateStatus(selectedFormulaOnThisPage.id, 'accepted');
                          onSelectFormula(null);
                        }}
                        className="p-1.5 hover:bg-emerald-600/30 text-emerald-400 rounded cursor-pointer transition flex items-center justify-center gap-1"
                        title="Accept Formula (Tick)"
                      >
                        <Check className="w-4 h-4 stroke-[2.5]" />
                        <span className="text-[11px] font-semibold text-emerald-300">Accept</span>
                      </button>
                      <button
                        type="button"
                        onMouseDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          onUpdateStatus(selectedFormulaOnThisPage.id, 'rejected');
                          onSelectFormula(null);
                        }}
                        className="p-1.5 hover:bg-amber-600/30 text-amber-400 rounded cursor-pointer transition flex items-center justify-center gap-1"
                        title="Reject Formula (Wrong)"
                      >
                        <X className="w-4 h-4 stroke-[2.5]" />
                        <span className="text-[11px] font-semibold text-amber-300">Reject</span>
                      </button>
                      <button
                        type="button"
                        onMouseDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteFormula(selectedFormulaOnThisPage.id);
                          onSelectFormula(null);
                        }}
                        className="p-1.5 hover:bg-rose-600/30 text-rose-400 rounded cursor-pointer transition flex items-center justify-center gap-1"
                        title="Delete Box"
                      >
                        <Trash2 className="w-4 h-4 stroke-[2.5]" />
                        <span className="text-[11px] font-semibold text-rose-300">Delete</span>
                      </button>
                    </>
                  ) : (
                    /* For existing tool-accepted box, show Delete Box alone */
                    <button
                      type="button"
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteFormula(selectedFormulaOnThisPage.id);
                        onSelectFormula(null);
                      }}
                      className="p-1.5 hover:bg-rose-600/30 text-rose-400 rounded cursor-pointer transition flex items-center justify-center gap-1 px-2"
                      title="Delete Box"
                    >
                      <Trash2 className="w-4 h-4 stroke-[2.5]" />
                      <span className="text-xs font-semibold text-rose-300">Delete Box</span>
                    </button>
                  )}
                </div>
              )}

              {/* PDF Page Image */}
              <img
                src={getPageImageUrl(docId, pageNum, zoom)}
                alt={`Page ${pageNum}`}
                loading={pageNum <= 3 ? 'eager' : 'lazy'}
                className="block max-w-none pointer-events-none w-full"
                style={{ width: `${612 * zoom}px` }}
              />

              {/* SVG Bounding Boxes Overlay for this page */}
              {showBoxes && (
                <svg
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  style={{ width: `${612 * zoom}px` }}
                >
                  {pageFormulas.map((f) => {
                    const [x0, y0, x1, y1] = f.bbox;
                    const isSelected = f.id === selectedFormulaId;

                    let boxClass = 'box-accepted';
                    if (f.status === 'uncertain') boxClass = 'box-uncertain';
                    if (f.status === 'rejected') boxClass = 'box-rejected';

                    return (
                      <g key={f.id}>
                        <rect
                          x={x0 * zoom}
                          y={y0 * zoom}
                          width={(x1 - x0) * zoom}
                          height={(y1 - y0) * zoom}
                          className={`${boxClass} stroke-2 transition-all cursor-pointer pointer-events-auto ${
                            isSelected ? 'stroke-rose-500 fill-rose-500/20 stroke-3' : ''
                          }`}
                          rx={2}
                          onMouseDown={(e) => {
                            e.stopPropagation();
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectFormula(isSelected ? null : f.id);
                          }}
                        />
                      </g>
                    );
                  })}

                  {/* Active Manual Draw Preview Rectangle on the page being drawn */}
                  {isDrawing && activeDrawPage === pageNum && drawStart && drawCurrent && (
                    <rect
                      x={Math.min(drawStart.x, drawCurrent.x) * zoom}
                      y={Math.min(drawStart.y, drawCurrent.y) * zoom}
                      width={Math.abs(drawCurrent.x - drawStart.x) * zoom}
                      height={Math.abs(drawCurrent.y - drawStart.y) * zoom}
                      className="stroke-rose-500 fill-rose-500/20 stroke-2 stroke-dasharray-4"
                    />
                  )}
                </svg>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
