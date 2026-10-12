import React, { useState } from 'react';
import { X, Sliders, ShieldCheck } from 'lucide-react';
import { AnnotationConfig } from '../types/formula';

interface ConfigModalProps {
  isOpen: boolean;
  config?: AnnotationConfig;
  onClose: () => void;
  onSave: (config: AnnotationConfig) => void;
}

const DEFAULT_CONFIG: AnnotationConfig = {
  border_width: 0.01,
  border_color: '#E31B23',
  fill_color: null,
  opacity: 1.0
};

export const ConfigModal: React.FC<ConfigModalProps> = ({
  isOpen,
  config = DEFAULT_CONFIG,
  onClose,
  onSave
}) => {
  const safeConfig = config || DEFAULT_CONFIG;
  const [borderWidth, setBorderWidth] = useState<number>(safeConfig.border_width ?? 0.01);
  const [borderColor, setBorderColor] = useState<string>(safeConfig.border_color ?? '#E31B23');
  const [opacity, setOpacity] = useState<number>(safeConfig.opacity ?? 1.0);
  const [onlyTaggedFormulas, setOnlyTaggedFormulas] = useState<boolean>(safeConfig.only_tagged_formulas ?? true);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave({
      border_width: borderWidth,
      border_color: borderColor,
      fill_color: null,
      opacity: opacity,
      only_tagged_formulas: onlyTaggedFormulas
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md p-6 shadow-2xl space-y-6">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-rose-400" />
            <h3 className="font-semibold text-slate-100">Rectangle Annotation Settings</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded text-slate-400 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form fields */}
        <div className="space-y-4 text-sm text-slate-300">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1 flex items-center justify-between">
              <span>Border Width (pt)</span>
              <span className="text-rose-400 font-mono text-[11px]">Client Default: 0.01 pt</span>
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="5.0"
              value={borderWidth}
              onChange={(e) => setBorderWidth(parseFloat(e.target.value) || 0.01)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 font-mono text-slate-100 focus:outline-none focus:border-rose-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Border Color
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="color"
                value={borderColor}
                onChange={(e) => setBorderColor(e.target.value)}
                className="w-10 h-10 rounded border border-slate-700 bg-transparent cursor-pointer"
              />
              <input
                type="text"
                value={borderColor}
                onChange={(e) => setBorderColor(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 font-mono text-slate-100 focus:outline-none focus:border-rose-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Fill Color
            </label>
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Transparent / No Fill</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800">
            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyTaggedFormulas}
                onChange={(e) => setOnlyTaggedFormulas(e.target.checked)}
                className="mt-0.5 rounded border-slate-700 bg-slate-950 text-rose-500 focus:ring-rose-500"
              />
              <div className="text-xs">
                <span className="font-semibold text-slate-200 block">Strict Tagged Formulas Only</span>
                <span className="text-slate-400 leading-relaxed block mt-0.5">
                  Only draws rectangles around formulas defined in PDF structure tags (/Formula, /Math). Prevents false positives on normal text.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md shadow-rose-950 cursor-pointer"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};
