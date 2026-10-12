"""
Layout Analysis & Bounding Box Grouping Module
Refines formula bounding boxes, handles right-aligned equation numbers,
and strictly prevents over-merging of separate equations or merging with paragraph text.
"""

import re
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from typing import List, Dict, Any

EQUATION_NUM_PATTERN = re.compile(r'^\s*[\(\[\{]\s*(\d+(\.\d+)*)\s*[\)\]\}]\s*$')

def exclude_equation_numbers(page: fitz.Page, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks if formula contains a right-aligned equation number e.g. (1) or (2.3).
    If found, clips the right boundary (x1) before the equation number.
    """
    spans = item.get("spans", [])
    if not spans or len(spans) < 2:
        return item

    page_width = page.rect.width
    last_span = spans[-1]
    last_text = last_span.get("text", "").strip()

    # If last span looks like an equation label (1) and is near right margin (> 65% page width)
    if EQUATION_NUM_PATTERN.match(last_text) and last_span.get("bbox", [0])[0] > (0.65 * page_width):
        clip_x1 = spans[-2].get("bbox")[2]
        item["bbox"][2] = clip_x1 + 0.5  # ultra-tight padding
        item["formula_text"] = "".join(s.get("text", "") for s in spans[:-1]).strip()
        item["has_equation_number"] = True
        item["equation_number"] = last_text

    return item

def group_and_merge_boxes(
    page: fitz.Page,
    candidates: List[Dict[str, Any]],
    padding_x: float = 0.5,
    padding_y: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Refines formula candidates and applies ultra-tight protective padding.
    Guarantees no merging across words, commas, or paragraph sentences.
    """
    if not candidates:
        return []

    # Handle right-aligned equation numbers
    processed = [exclude_equation_numbers(page, dict(c)) for c in candidates]

    # Sort candidates by top coordinate (y0), then left coordinate (x0)
    processed.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

    merged: List[Dict[str, Any]] = []

    for item in processed:
        bbox = item["bbox"]
        
        if not merged:
            merged.append(item)
            continue

        prev = merged[-1]
        prev_bbox = prev["bbox"]

        # Only merge if boxes are directly touching/overlapping fragments of the same formula (gap < 2pt)
        same_line = abs(bbox[1] - prev_bbox[1]) < 2.0 and abs(bbox[3] - prev_bbox[3]) < 2.0
        horizontal_gap = bbox[0] - prev_bbox[2]

        if same_line and 0.0 <= horizontal_gap < 2.0:
            # Merge fragments of the exact same formula token
            new_bbox = [
                min(prev_bbox[0], bbox[0]),
                min(prev_bbox[1], bbox[1]),
                max(prev_bbox[2], bbox[2]),
                max(prev_bbox[3], bbox[3])
            ]
            prev["bbox"] = new_bbox
            prev["formula_text"] = f"{prev['formula_text']} {item['formula_text']}"
            prev["confidence"] = max(prev["confidence"], item["confidence"])
        else:
            merged.append(item)

    # Apply ultra-tight padding without exceeding page bounds
    page_w, page_h = page.rect.width, page.rect.height
    for item in merged:
        b = item["bbox"]
        item["bbox"] = [
            round(max(0.0, b[0] - padding_x), 2),
            round(max(0.0, b[1] - padding_y), 2),
            round(min(page_w, b[2] + padding_x), 2),
            round(min(page_h, b[3] + padding_y), 2)
        ]
        item.pop("spans", None)

    return merged
