import axios from 'axios';
import { DocumentState, FormulaDetection, AnnotationConfig, BenchmarkReport } from '../types/formula';

const API_BASE = '/api';

export async function uploadPdfFile(file: File): Promise<DocumentState> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post<DocumentState>(`${API_BASE}/upload`, formData);
  return response.data;
}

export async function getDocumentState(docId: string): Promise<DocumentState> {
  const response = await axios.get<DocumentState>(`${API_BASE}/document/${docId}`);
  return response.data;
}

export function getPageImageUrl(docId: string, pageNum: number, zoom: number = 1.5): string {
  return `${API_BASE}/page-image/${docId}/${pageNum}?zoom=${zoom}`;
}

export async function updateFormulaStatus(docId: string, formulaId: string, status: string) {
  const response = await axios.post(`${API_BASE}/detection/update/${docId}`, {
    action: 'update_status',
    formula_id: formulaId,
    status: status
  });
  return response.data;
}

export async function addManualFormula(docId: string, formula: Partial<FormulaDetection>) {
  const response = await axios.post(`${API_BASE}/detection/update/${docId}`, {
    action: 'add',
    formula: formula
  });
  return response.data;
}

export async function updateFormulaBbox(docId: string, formulaId: string, bbox: [number, number, number, number]) {
  const response = await axios.post(`${API_BASE}/detection/update/${docId}`, {
    action: 'update_bbox',
    formula_id: formulaId,
    bbox: bbox
  });
  return response.data;
}

export async function deleteFormula(docId: string, formulaId: string) {
  const response = await axios.post(`${API_BASE}/detection/update/${docId}`, {
    action: 'delete',
    formula_id: formulaId
  });
  return response.data;
}

export async function updateAnnotationConfig(docId: string, config: Partial<AnnotationConfig>) {
  const response = await axios.post(`${API_BASE}/config/update/${docId}`, config);
  return response.data;
}

export async function exportAnnotatedPdf(docId: string) {
  const response = await axios.post(`${API_BASE}/export/${docId}`);
  return response.data;
}

export async function runBenchmarkSuite(): Promise<BenchmarkReport> {
  const response = await axios.get<BenchmarkReport>(`${API_BASE}/benchmark/run`);
  return response.data;
}
