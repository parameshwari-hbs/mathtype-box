"""
PDF Safety & Validation Module
Checks PDF security restrictions, digital signatures, encryption, and verifies exported document integrity.
"""

import os
import fitz
from typing import Dict, Any, List

def check_pdf_security(file_path: str) -> Dict[str, Any]:
    """
    Inspects input PDF file for encryption, digital signatures, and permissions.
    """
    if not os.path.exists(file_path):
        return {"valid": False, "error": "File does not exist"}

    warnings: List[str] = []
    
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return {"valid": False, "error": f"Failed to open PDF document: {str(e)}"}

    if doc.is_encrypted:
        return {"valid": False, "error": "PDF is encrypted/password protected. Decrypt document before processing."}

    # Check for digital signatures or permissions
    try:
        # Check permissions bitmask
        perms = doc.permissions
        # Perm 4: modify annotations (0x10)
        if perms > 0 and not (perms & 16):
            warnings.append("Document permissions restrict annotation modification.")
    except Exception:
        pass

    # Check for digital signature fields
    has_signatures = False
    for page in doc:
        for widget in page.widgets():
            if widget.field_type_string == "Signature":
                has_signatures = True
                warnings.append("Document contains digital signatures. Adding annotations may invalidate existing signatures.")
                break
        if has_signatures:
            break

    page_count = len(doc)
    doc.close()

    return {
        "valid": True,
        "page_count": page_count,
        "is_encrypted": False,
        "has_signatures": has_signatures,
        "warnings": warnings
    }

def validate_exported_pdf(output_path: str, expected_page_count: int, expected_annotations_count: int) -> Dict[str, Any]:
    """
    Verifies that the output PDF was saved properly and opens cleanly.
    """
    if not os.path.exists(output_path):
        return {"success": False, "error": "Output PDF file was not created."}

    try:
        doc = fitz.open(output_path)
        actual_page_count = len(doc)
        
        if actual_page_count != expected_page_count:
            doc.close()
            return {"success": False, "error": f"Page count mismatch: expected {expected_page_count}, got {actual_page_count}"}

        actual_annots = 0
        for page in doc:
            annot = page.first_annot
            while annot:
                if annot.type[1] in ("Square", "Rectangle"):
                    actual_annots += 1
                annot = annot.next

        doc.close()

        return {
            "success": True,
            "page_count": actual_page_count,
            "annotations_count": actual_annots,
            "expected_annotations": expected_annotations_count,
            "verified": True
        }
    except Exception as e:
        return {"success": False, "error": f"Output PDF verification failed: {str(e)}"}
