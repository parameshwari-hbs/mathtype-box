"""
Hybrid Formula Detection Pipeline Engine
Prioritizes Tagged Structure Tree (/Formula, /Math) explicit tags.
When formula tags are present, exclusively detects tagged formulas to eliminate false positives.
Provides native text heuristics and OCR only for untagged legacy PDFs.
"""

import fitz
from typing import List, Dict, Any
from app.detection.struct_tree import extract_struct_tree_formulas, has_struct_tree_formulas
from app.detection.text_analysis import extract_text_span_candidates
from app.detection.layout_analysis import group_and_merge_boxes
from app.detection.ocr_engine import detect_scanned_formulas
from app.pdf_processor.preservation import deduplicate_detections

def run_hybrid_formula_detection(doc: fitz.Document, only_tagged: bool = False) -> List[Dict[str, Any]]:
    """
    Runs formula detection pipeline across all pages of the document.
    
    If the document has tagged formulas or only_tagged is True:
    Exclusively detects formulas from PDF /Formula and /Math tags with 100% precision.
    No other text or heuristics will be annotated.
    
    Returns list of formula detection objects with page_num, bbox, method, confidence, status, etc.
    """
    all_formulas: List[Dict[str, Any]] = []
    is_tagged_pdf = has_struct_tree_formulas(doc)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Stage 1: Explicit StructTree / Tagged formulas
        struct_formulas = extract_struct_tree_formulas(doc, page_num)

        # If tagged formulas are present or user requested only tagged formulas:
        # Strictly use tagged formulas — do NOT guess or add false positives.
        if is_tagged_pdf or only_tagged or len(struct_formulas) > 0:
            page_candidates = list(struct_formulas)
        else:
            # Fallback for untagged legacy PDFs only
            native_candidates = extract_text_span_candidates(page, page_num)
            grouped_native = group_and_merge_boxes(page, native_candidates)
            page_candidates = list(struct_formulas) + grouped_native

            # Scanned PDF Fallback if page text density is low
            text_content = page.get_text("text").strip()
            if len(text_content) < 50:
                ocr_candidates = detect_scanned_formulas(page, page_num)
                page_candidates.extend(ocr_candidates)

        # Deduplicate against pre-existing PDF annotations
        fresh_boxes, existing_boxes = deduplicate_detections(page, page_candidates)
        page_candidates = fresh_boxes + existing_boxes

        # Assign unique IDs and format output
        for idx, item in enumerate(page_candidates, start=1):
            item["id"] = f"formula_p{page_num + 1}_{idx}"
            if "status" not in item:
                item["status"] = "accepted" if item.get("confidence", 0) >= 0.75 else "uncertain"
            all_formulas.append(item)

    return all_formulas
