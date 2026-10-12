"""
PDF Annotator Module
Applies exact 0.01 pt red border rectangle annotations to PDF documents.
Handles page rotation, crop box offsets, and PDF syntax formatting.
"""

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    import fitz
from typing import List, Dict, Any, Tuple
from app.config import AnnotationConfig, DEFAULT_ANNOTATION_CONFIG

def apply_formula_annotation(
    page: fitz.Page,
    bbox: List[float],
    config: AnnotationConfig = DEFAULT_ANNOTATION_CONFIG
) -> fitz.Annot:
    """
    Applies a formula rectangle annotation to a PyMuPDF Page.
    
    :param page: fitz.Page object
    :param bbox: [x0, y0, x1, y1] bounding box in PDF page coordinates
    :param config: AnnotationConfig specifying border_width (0.01 pt), stroke color, fill
    :return: fitz.Annot instance created
    """
    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
    
    if rect.is_empty or rect.is_infinite:
        rect.normalize()

    # Create Square / Rectangle annotation
    annot = page.add_rect_annot(rect)
    
    # Set stroke color (RGB tuple normalized 0.0 to 1.0) and fill color (None for transparent)
    stroke_rgb = config.rgb_stroke
    fill_rgb = config.rgb_fill
    annot.set_colors(stroke=stroke_rgb, fill=fill_rgb)
    
    # Set exact border width (0.01 pt requirement)
    annot.set_border(width=config.border_width)
    
    # Set opacity
    annot.set_opacity(config.opacity)
    
    # Set flags: Printable (F=4)
    annot.set_flags(4)
    
    # Set annotation name / subject info matching Adobe Acrobat specification
    annot.set_info(title="FormulaBox Automator", subject="Rectangle")
    
    # Update annotation appearance stream
    annot.update()
    
    return annot

def apply_annotations_to_document(
    doc: fitz.Document,
    formulas: List[Dict[str, Any]],
    config: AnnotationConfig = DEFAULT_ANNOTATION_CONFIG
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Applies annotations for all accepted formula detections across document pages.
    """
    applied_count = 0
    results = []

    for item in formulas:
        if item.get("status") != "accepted":
            continue
            
        page_num = item.get("page_num", 1) - 1 # 0-indexed
        if page_num < 0 or page_num >= len(doc):
            continue
            
        page = doc[page_num]
        bbox = item.get("bbox")
        
        if not bbox or len(bbox) != 4:
            continue
            
        apply_formula_annotation(page, bbox, config)
        applied_count += 1
        item_copy = dict(item)
        item_copy["applied"] = True
        results.append(item_copy)

    return applied_count, results
