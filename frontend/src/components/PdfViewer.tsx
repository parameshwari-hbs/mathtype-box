import React, { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Eye, EyeOff, PlusCircle, Check, X, Trash2 } from 'lucide-react';
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
  const [drawMode, setDrawMode] = useState<boolean>(false);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Filter formulas for current page
  const pageFormulas = formulas.filter(f => f.page_num === currentPage);

  // Handle manual drawing on canvas
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!drawMode || !imageRef.current) return;
    const rect = imageRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    setDrawStart({ x, y });
    setDrawCurrent({ x, y });
    setIsDrawing(true);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !drawMode || !imageRef.current) return;
    const rect = imageRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    setDrawCurrent({ x, y });
  };

  const handleMouseUp = () => {
    if (!isDrawing || !drawStart || !drawCurrent) return;
    setIsDrawing(false);
    
    const x0 = Math.min(drawStart.x, drawCurrent.x);
    const y0 = Math.min(drawStart.y, drawCurrent.y);
    const x1 = Math.max(drawStart.x, drawCurrent.x);
    const y1 = Math.max(drawStart.y, drawCurrent.y);

    // Only add if box has reasonable width and height
    if (x1 - x0 > 10 && y1 - y0 > 10) {
      onAddManualFormula(currentPage, [
        Math.round(x0 * 100) / 100,
        Math.round(y0 * 100) / 100,
        Math.round(x1 * 100) / 100,
        Math.round(y1 * 100) / 100
      ]);
    }

    setDrawStart(null);
    setDrawCurrent(null);
    setDrawMode(false);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden relative">
      {/* Control Toolbar */}
      <div className="h-12 bg-slate-900 px-6 flex items-center justify-between border-b border-slate-800 z-10">
        {/* Page Navigation */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 cursor-pointer"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <span className="text-sm font-medium text-slate-300">
            Page <span className="text-slate-100 font-bold">{currentPage}</span> of {totalPages}
          </span>

          <button
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 cursor-pointer"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
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

          <button
            onClick={() => setDrawMode(!drawMode)}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
              drawMode ? 'bg-rose-600 text-white shadow-md shadow-rose-900/40 animate-pulse' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>{drawMode ? 'Click & Drag to Draw Box' : 'Add Manual Box'}</span>
          </button>

          {/* Zoom Buttons */}
          <div className="flex items-center bg-slate-800 rounded border border-slate-700 p-0.5">
            <button
              onClick={() => setZoom(Math.max(0.75, zoom - 0.25))}
              className="p-1 hover:bg-slate-700 rounded text-slate-300 cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono px-2 text-slate-300">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom(Math.min(2.5, zoom + 0.25))}
              className="p-1 hover:bg-slate-700 rounded text-slate-300 cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Render Area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-8 flex items-center justify-center relative select-none"
      >
        <div
          className="relative shadow-2xl rounded border border-slate-800 bg-white"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          {/* PDF Page Image */}
          <img
            ref={imageRef}
            src={getPageImageUrl(docId, currentPage, zoom)}
            alt={`Page ${currentPage}`}
            className="block max-w-none pointer-events-none"
            style={{ width: `${612 * zoom}px` }}
          />

          {/* SVG Bounding Boxes Overlay */}
          {showBoxes && (
            <svg
              className="absolute inset-0 w-full h-full pointer-events-auto"
              style={{ width: `${612 * zoom}px` }}
            >
              {pageFormulas.map((f) => {
                const [x0, y0, x1, y1] = f.bbox;
                const isSelected = f.id === selectedFormulaId;
                
                let boxClass = 'box-accepted';
                if (f.status === 'uncertain') boxClass = 'box-uncertain';
                if (f.status === 'rejected') boxClass = 'box-rejected';

                return (
                  <g key={f.id} onClick={() => onSelectFormula(f.id)}>
                    <rect
                      x={x0 * zoom}
                      y={y0 * zoom}
                      width={(x1 - x0) * zoom}
                      height={(y1 - y0) * zoom}
                      className={`${boxClass} stroke-2 transition-all cursor-pointer ${
                        isSelected ? 'stroke-rose-500 fill-rose-500/20 stroke-3' : ''
                      }`}
                      rx={2}
                    />

                    {/* Popover actions when selected */}
                    {isSelected && (
                      <foreignObject
                        x={x0 * zoom}
                        y={Math.max(0, (y0 * zoom) - 36)}
                        width={180}
                        height={34}
                      >
                        <div className="flex items-center space-x-1 bg-slate-900/90 text-white rounded p-1 shadow-lg border border-slate-700 text-xs">
                          <button
                            onClick={(e) => { e.stopPropagation(); onUpdateStatus(f.id, 'accepted'); }}
                            className="p-1 hover:bg-emerald-600/30 text-emerald-400 rounded cursor-pointer"
                            title="Accept Formula"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); onUpdateStatus(f.id, 'rejected'); }}
                            className="p-1 hover:bg-amber-600/30 text-amber-400 rounded cursor-pointer"
                            title="Reject Formula"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); onDeleteFormula(f.id); }}
                            className="p-1 hover:bg-rose-600/30 text-rose-400 rounded cursor-pointer"
                            title="Delete Box"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </foreignObject>
                    )}
                  </g>
                );
              })}

              {/* Active Manual Draw Preview Rectangle */}
              {isDrawing && drawStart && drawCurrent && (
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
      </div>
    </div>
  );
};
