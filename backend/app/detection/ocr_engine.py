"""
Scanned PDF & Layout OCR Detection Module
Uses page image rendering and computer vision layout segmentation for image-based PDFs.
"""

try:
    import pymupdf as fitz
except ImportError:
    import fitz
import cv2
import numpy as np
from typing import List, Dict, Any

def detect_scanned_formulas(page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
    """
    Analyzes scanned / raster PDF page images for candidate formula bounding boxes.
    """
    candidates = []
    # Render page to Pixmap at 2.0 scale (approx 150-200 DPI)
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    # Convert PyMuPDF Pixmap to OpenCV numpy image
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Binarize image
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Horizontal morphological kernel to detect text line blocks
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    page_w, page_h = page.rect.width, page.rect.height
    scale_x = page_w / pix.width
    scale_y = page_h / pix.height

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Filter small noise or entire page outlines
        if w < 30 or h < 10 or (w > 0.95 * pix.width and h > 0.95 * pix.height):
            continue

        # Extract ROI in original grayscale image to check features
        roi = gray[y:y+h, x:x+w]
        if roi.size == 0:
            continue

        # Check for horizontal fraction lines or operator signatures
        edges = cv2.Canny(roi, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=20, minLineLength=15, maxLineGap=5)
        
        has_fraction_line = lines is not None and len(lines) > 0

        # Convert image coordinates back to PDF points
        pdf_x0 = x * scale_x
        pdf_y0 = y * scale_y
        pdf_x1 = (x + w) * scale_x
        pdf_y1 = (y + h) * scale_y

        if has_fraction_line or (w / float(h)) > 2.0:
            candidates.append({
                "page_num": page_num + 1,
                "bbox": [round(pdf_x0, 2), round(pdf_y0, 2), round(pdf_x1, 2), round(pdf_y1, 2)],
                "formula_text": "[Scanned Formula Region]",
                "detection_method": "layout_ocr",
                "formula_type": "display",
                "confidence": 0.65,
                "status": "uncertain"  # Flag for manual verification on scanned pages
            })

    return candidates
