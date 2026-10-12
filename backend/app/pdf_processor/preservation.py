"""
PDF Preservation & Deduplication Module
Ensures existing document structure, tags, text, fonts, and annotations are preserved.
Detects pre-existing rectangle annotations to prevent duplicates.
"""

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from typing import List, Dict, Any, Tuple

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """Calculates Intersection over Union (IoU) between two bounding boxes [x0, y0, x1, y1]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea <= 0:
        return 0.0

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    return iou

def get_existing_annotations(page: fitz.Page) -> List[Dict[str, Any]]:
    """Reads existing annotations from a PDF page safely."""
    existing = []
    try:
        annot = page.first_annot
        while annot:
            try:
                rect = annot.rect
                info = annot.info or {}
                annot_type = annot.type[1] if annot.type else "Square"
                existing.append({
                    "type": annot_type,
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "title": info.get("title", ""),
                    "subject": info.get("subject", "")
                })
            except Exception:
                pass
            annot = annot.next
    except Exception:
        pass
    return existing

def deduplicate_detections(
    page: fitz.Page,
    detected_boxes: List[Dict[str, Any]],
    iou_threshold: float = 0.75
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Compares newly detected formula boxes with existing annotations on the page.
    Returns (fresh_detections, duplicate_or_existing_detections).
    """
    existing_annots = get_existing_annotations(page)
    existing_rects = [a["bbox"] for a in existing_annots if a["type"] in ("Square", "Rectangle", "SquareAnnotation")]

    fresh = []
    duplicates = []

    for item in detected_boxes:
        bbox = item.get("bbox")
        if not bbox:
            continue
            
        is_dup = False
        for ex_bbox in existing_rects:
            if calculate_iou(bbox, ex_bbox) >= iou_threshold:
                is_dup = True
                break
                
        if is_dup:
            item_copy = dict(item)
            item_copy["status"] = "existing"
            item_copy["note"] = "Already annotated in original document"
            duplicates.append(item_copy)
        else:
            fresh.append(item)

    return fresh, duplicates
