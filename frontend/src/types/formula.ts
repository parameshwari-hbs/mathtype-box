export type FormulaStatus = 'accepted' | 'uncertain' | 'rejected' | 'existing';
export type FormulaType = 'inline' | 'display' | 'multiline' | 'table_formula';
export type DetectionMethod = 'struct_tree' | 'native_text' | 'layout_ocr' | 'manual';

export interface FormulaDetection {
  id: string;
  page_num: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1] in PDF points
  formula_text: string;
  detection_method: DetectionMethod;
  formula_type: FormulaType;
  confidence: number;
  status: FormulaStatus;
  has_equation_number?: boolean;
  equation_number?: string;
  applied?: boolean;
  note?: string;
}

export interface AnnotationConfig {
  border_width: number;
  border_color: string;
  fill_color: string | null;
  opacity: number;
  only_tagged_formulas?: boolean;
}

export interface DocumentStats {
  total_detected: number;
  accepted_count: number;
  uncertain_count: number;
  rejected_count?: number;
  applied_count: number;
}

export interface DocumentState {
  doc_id: string;
  filename: string;
  total_pages: number;
  stats: DocumentStats;
  warnings?: string[];
  config: AnnotationConfig;
  formulas: FormulaDetection[];
}

export interface BenchmarkReport {
  file_name: string;
  total_pages: number;
  total_detected_formulas: number;
  accepted_formulas: number;
  uncertain_formulas: number;
  existing_annotations: number;
  estimated_precision: number;
  page_breakdown: Record<number, number>;
  detections: FormulaDetection[];
}
