"""
FormulaBox Automator - FastAPI Main Server Entry Point
Provides API endpoints for PDF upload, page rendering, formula detection, review state management, export, and benchmarking.
"""

import os
import uuid
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from typing import Dict, Any, List

from app.config import AnnotationConfig, DEFAULT_ANNOTATION_CONFIG
from app.pdf_processor.validator import check_pdf_security, validate_exported_pdf
from app.pdf_processor.annotator import apply_annotations_to_document
from app.detection.hybrid_engine import run_hybrid_formula_detection
from app.validation.test_generator import generate_sample_test_pdf
from app.validation.benchmark import run_accuracy_benchmark

app = FastAPI(
    title="FormulaBox Automator API",
    description="Automated PDF Formula Detection & 0.01pt Red Rectangle Annotation Engine",
    version="1.0.0"
)

# Enable CORS for frontend app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
UPLOAD_DIR = os.path.abspath("temp_uploads")
EXPORT_DIR = os.path.abspath("temp_exports")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# In-memory document sessions storage
DOCUMENTS_DB: Dict[str, Dict[str, Any]] = {}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "FormulaBox Automator", "version": "1.0.0"}

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Uploads a PDF, validates security, runs formula detection, and initializes document state."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")

    # Save uploaded file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Validate security & permissions
    security_info = check_pdf_security(file_path)
    if not security_info.get("valid"):
        raise HTTPException(status_code=400, detail=security_info.get("error"))

    # Open PyMuPDF document & run formula detection
    try:
        doc = fitz.open(file_path)
        formulas = run_hybrid_formula_detection(doc)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF: {str(e)}")

    # Store state
    doc_state = {
        "doc_id": doc_id,
        "filename": file.filename,
        "file_path": file_path,
        "total_pages": total_pages,
        "security": security_info,
        "formulas": formulas,
        "config": DEFAULT_ANNOTATION_CONFIG.dict()
    }
    DOCUMENTS_DB[doc_id] = doc_state

    # Summary statistics
    total_detected = len(formulas)
    accepted_count = sum(1 for f in formulas if f.get("status") == "accepted")
    uncertain_count = sum(1 for f in formulas if f.get("status") == "uncertain")

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "total_pages": total_pages,
        "stats": {
            "total_detected": total_detected,
            "accepted_count": accepted_count,
            "uncertain_count": uncertain_count,
            "applied_count": 0
        },
        "warnings": security_info.get("warnings", []),
        "formulas": formulas
    }

@app.get("/api/document/{doc_id}")
def get_document(doc_id: str):
    """Retrieves current state and formula detections for a document."""
    if doc_id not in DOCUMENTS_DB:
        raise HTTPException(status_code=404, detail="Document session not found.")
    
    state = DOCUMENTS_DB[doc_id]
    formulas = state["formulas"]

    total_detected = len(formulas)
    accepted_count = sum(1 for f in formulas if f.get("status") == "accepted")
    uncertain_count = sum(1 for f in formulas if f.get("status") == "uncertain")
    rejected_count = sum(1 for f in formulas if f.get("status") == "rejected")

    return {
        "doc_id": doc_id,
        "filename": state["filename"],
        "total_pages": state["total_pages"],
        "stats": {
            "total_detected": total_detected,
            "accepted_count": accepted_count,
            "uncertain_count": uncertain_count,
            "rejected_count": rejected_count,
            "applied_count": accepted_count
        },
        "config": state["config"],
        "formulas": formulas
    }

@app.get("/api/page-image/{doc_id}/{page_num}")
def get_page_image(doc_id: str, page_num: int, zoom: float = Query(default=1.5, ge=0.5, le=3.0)):
    """Renders a specific PDF page as PNG image for visual canvas display."""
    if doc_id not in DOCUMENTS_DB:
        raise HTTPException(status_code=404, detail="Document session not found.")
    
    state = DOCUMENTS_DB[doc_id]
    file_path = state["file_path"]

    if page_num < 1 or page_num > state["total_pages"]:
        raise HTTPException(status_code=400, detail="Page number out of bounds.")

    try:
        doc = fitz.open(file_path)
        page = doc[page_num - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        doc.close()

        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render page image: {str(e)}")

@app.post("/api/detection/update/{doc_id}")
def update_detections(doc_id: str, payload: Dict[str, Any] = Body(...)):
    """Updates formula box statuses or adds/edits/deletes formula detections."""
    if doc_id not in DOCUMENTS_DB:
        raise HTTPException(status_code=404, detail="Document session not found.")

    state = DOCUMENTS_DB[doc_id]
    action = payload.get("action")  # 'update_status', 'add', 'update_bbox', 'delete'

    if action == "update_status":
        formula_id = payload.get("formula_id")
        new_status = payload.get("status")  # 'accepted', 'rejected', 'uncertain'
        for f in state["formulas"]:
            if f["id"] == formula_id:
                f["status"] = new_status
                break
    elif action == "add":
        new_formula = payload.get("formula")
        if new_formula:
            page_num = new_formula.get("page_num", 1)
            f_id = new_formula.get("id") or f"formula_manual_p{page_num}_{uuid.uuid4().hex[:6]}"
            new_formula["id"] = f_id
            new_formula["detection_method"] = "manual"
            new_formula["confidence"] = 1.00
            new_formula["status"] = "accepted"
            state["formulas"].append(new_formula)
            return {"status": "updated", "formula": new_formula, "formulas_count": len(state["formulas"])}
    elif action == "update_bbox":
        formula_id = payload.get("formula_id")
        new_bbox = payload.get("bbox")
        for f in state["formulas"]:
            if f["id"] == formula_id:
                f["bbox"] = new_bbox
                break
    elif action == "delete":
        formula_id = payload.get("formula_id")
        state["formulas"] = [f for f in state["formulas"] if f["id"] != formula_id]

    return {"status": "updated", "formulas_count": len(state["formulas"])}

@app.post("/api/config/update/{doc_id}")
def update_config(doc_id: str, config_data: Dict[str, Any] = Body(...)):
    """Updates annotation export configuration (border width, color, opacity, fill)."""
    if doc_id not in DOCUMENTS_DB:
        raise HTTPException(status_code=404, detail="Document session not found.")
    
    state = DOCUMENTS_DB[doc_id]
    state["config"].update(config_data)
    return {"status": "updated", "config": state["config"]}

@app.post("/api/export/{doc_id}")
def export_pdf(doc_id: str):
    """Applies exact 0.01 pt red rectangle annotations to accepted formulas and exports a new PDF."""
    if doc_id not in DOCUMENTS_DB:
        raise HTTPException(status_code=404, detail="Document session not found.")

    state = DOCUMENTS_DB[doc_id]
    original_path = state["file_path"]
    formulas = state["formulas"]
    config_dict = state["config"]

    annot_config = AnnotationConfig(**config_dict)

    output_filename = f"annotated_{state['filename']}"
    output_path = os.path.join(EXPORT_DIR, f"{doc_id}_{output_filename}")

    try:
        doc = fitz.open(original_path)
        applied_count, results = apply_annotations_to_document(doc, formulas, annot_config)
        doc.save(output_path)
        doc.close()

        # Run export validation
        val_res = validate_exported_pdf(output_path, state["total_pages"], applied_count)
        if not val_res.get("success"):
            raise HTTPException(status_code=500, detail=val_res.get("error"))

        return {
            "status": "success",
            "output_filename": output_filename,
            "export_url": f"/api/download/{doc_id}",
            "applied_count": applied_count,
            "validation": val_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")

@app.get("/api/download/{doc_id}")
def download_exported_pdf(doc_id: str):
    """Downloads the exported annotated PDF file."""
    if doc_id not in DOCUMENTS_DB:
        raise HTTPException(status_code=404, detail="Document session not found.")
    
    state = DOCUMENTS_DB[doc_id]
    output_filename = f"annotated_{state['filename']}"
    output_path = os.path.join(EXPORT_DIR, f"{doc_id}_{output_filename}")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Exported file not found. Run export first.")

    return FileResponse(output_path, media_type="application/pdf", filename=output_filename)

@app.get("/api/benchmark/run")
def run_benchmark():
    """Generates synthetic math PDF and executes accuracy validation suite benchmark."""
    bench_path = os.path.join(UPLOAD_DIR, "benchmark_sample.pdf")
    generate_sample_test_pdf(bench_path)
    report = run_accuracy_benchmark(bench_path)
    return report
