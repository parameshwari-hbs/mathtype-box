# FormulaBox Automator

**FormulaBox Automator** is a standalone, precision desktop and web application designed to automate drawing rectangle annotations around every mathematical formula in a PDF document.

It creates compliant **0.01 pt red border rectangle annotations with transparent fill** matching the Adobe Acrobat color palette specification, preserving existing document vectors, tags, layers, and text without rasterization or destructive modifications.

---

## Key Features

1. **Mandatory Client Specification Compliance**:
   - **Annotation Type**: `Square` / `Rectangle`.
   - **Border Width**: Exactly `0.01 pt` (configurable).
   - **Border Color**: Red (`#E31B23` / RGB `[0.890, 0.106, 0.141]`).
   - **Fill**: Transparent / No Fill.
   - **Opacity**: `1.0`.

2. **Hybrid Formula Detection Pipeline**:
   - **StructTree Verification**: Prioritizes tagged formula elements (`/Formula`, `/Math`).
   - **Native PDF Text & Operator Analysis**: Detects math operators (`=`, `≠`, `±`, `×`, `÷`, `≤`, `≥`, `∑`, `∫`, `√`, `∞`, Greek symbols), superscripts, subscripts, fractions, and math fonts (`CMSY`, `Symbol`, `STIX`, etc.).
   - **Layout Analysis**: Identifies inline equations, standalone/display equations, multi-line equations, and right-aligned equation numbers like `(1.1)`.
   - **Scanned PDF Layout Engine**: Computer vision layout analysis for image-based/scanned PDFs.
   - **False Positive Filtering**: Excludes dates, URLs, section headings, ordinary prose slashes (`and/or`), and page numbers.

3. **PDF Preservation & Security**:
   - Original PDF is **NEVER** modified or overwritten.
   - Output is saved as a new separate PDF file.
   - Detects existing annotations to prevent duplicates.
   - Preserves text, images, fonts, links, crop boxes, and structure trees without rasterizing digital PDFs.
   - Performs security checks for passwords and digital signatures.

4. **Interactive Review Workspace**:
   - High-performance visual PDF viewer with zoom controls.
   - Color-coded bounding box overlays.
   - Interactive Accept / Reject / Delete / Manual Add controls.
   - One-click "Accept All ≥ 75% Confidence" formula batch approval.

5. **Validation Suite & Accuracy Metrics**:
   - Built-in validation benchmark calculating Precision, Recall, and Box Overlap metrics.

---

## Directory Structure

```
FORMULA_BOX/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI REST Server & Endpoints
│   │   ├── config.py              # 0.01 pt Red Border Annotation Configs
│   │   ├── detection/
│   │   │   ├── hybrid_engine.py   # Multi-stage Formula Detection Pipeline
│   │   │   ├── struct_tree.py     # Tagged PDF Structure Parser
│   │   │   ├── text_analysis.py   # Native Text Span & Symbol Analyzer
│   │   │   ├── layout_analysis.py # Layout Grouping & Equation Numbers
│   │   │   ├── ocr_engine.py      # Scanned PDF Layout Segmentation
│   │   │   └── false_positive.py  # Date/URL/Prose Filtering
│   │   ├── pdf_processor/
│   │   │   ├── annotator.py       # Exact PDF Rectangle Annotation Generator
│   │   │   ├── preservation.py    # Tag Preservation & Deduplication
│   │   │   └── validator.py       # PDF Security & Post-Export Verification
│   │   └── validation/
│   │       ├── benchmark.py       # Precision/Recall Validation Engine
│   │       └── test_generator.py # Synthetic PDF Generator
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── StatsBar.tsx
│   │   │   ├── PdfViewer.tsx
│   │   │   ├── SidebarList.tsx
│   │   │   └── ConfigModal.tsx
│   │   ├── api/client.ts
│   │   └── types/formula.ts
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   └── test_detection.py         # Unit & Integration Tests
├── run_app.py                      # Standalone App Launcher
├── build_exe.py                    # Windows Executable Packager
└── README.md
```

---

## Installation & Setup

### Prerequisites
- **Python 3.12+**
- **Node.js v18+ & npm**

### 1. Python Environment Setup

```bash
# Navigate to project root
cd FormulaBoxAutomator

# Install backend dependencies
python -m pip install -r backend/requirements.txt
```

### 2. Frontend Build Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Build static bundle for production
npm run build

# Return to root directory
cd ..
```

---

## Execution Instructions

### Running the Application (Desktop / Browser)

Launch the standalone app with a single command:

```bash
python run_app.py
```

This will automatically:
1. Start the FastAPI backend server on `http://127.0.0.1:8000`.
2. Open your default web browser to the interactive FormulaBox Automator workspace.

---

## Running Unit Tests & Benchmarks

Run the complete backend test suite:

```bash
python -m unittest discover tests
```

---

## Windows Packaging Instructions (PyInstaller)

To build a single standalone Windows executable (`FormulaBoxAutomator.exe`) that runs without requiring Python or Node installed:

```bash
python build_exe.py
```

The output executable will be created at:
`dist/FormulaBoxAutomator.exe`

---

## Troubleshooting & Verification

1. **Border Width Verification**:
   - Open the exported PDF in Adobe Acrobat.
   - Right-click the red rectangle around any formula -> select **Properties**.
   - Verify: **Line Thickness = 0.01 pt**, **Color = Red**, **Fill = None**.

2. **Scanned PDF Processing**:
   - For image-based PDFs, FormulaBox Automator uses image segmentation layout analysis to detect formula blocks and flags them for human review with an amber border.

3. **Digital Signatures & Encryption**:
   - If a PDF is password protected or digitally signed, FormulaBox Automator will notify you with a warning prior to processing.
