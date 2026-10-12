"""
Synthetic PDF Generator for FormulaBox Automator Validation Suite
Programmatically generates test PDFs with inline math, display math, fractions, radicals, equation numbers, tables, and non-math prose.
"""

import os
try:
    import pymupdf as fitz
except ImportError:
    import fitz

def generate_sample_test_pdf(output_path: str) -> str:
    """
    Generates a multi-page sample PDF containing various mathematical formulas and prose text.
    """
    doc = fitz.open()

    # Page 1: Digital Math Formulas (Inline & Display)
    page1 = doc.new_page(width=612, height=792)  # Letter size
    
    text_p1 = """
FormulaBox Automator - Benchmark Test Page 1

1. Inline Formula:
Consider the standard quadratic function f(x) = a x^2 + b x + c where a ≠ 0.

2. Standalone Display Equation:
                                    E = m c^2

3. Integral Formula:
                                  ∫_{0}^{∞} e^{-x^2} dx = √π / 2

4. Summation Formula:
                                  ∑_{i=1}^{n} i = n(n + 1) / 2
"""
    page1.insert_text((50, 50), text_p1, fontsize=12)

    # Page 2: Equation Numbers & Fractions
    page2 = doc.new_page(width=612, height=792)
    text_p2 = """
Benchmark Test Page 2 - Multi-line Equations & Equation Numbers

Einstein Field Equation:
                                  G_{μν} + Λ g_{μν} = (8 π G / c^4) T_{μν}          (1.1)

Pythagorean Theorem:
                                  a^2 + b^2 = c^2                                 (1.2)
"""
    page2.insert_text((50, 50), text_p2, fontsize=12)

    # Page 3: Non-Formula Prose (False Positive Controls)
    page3 = doc.new_page(width=612, height=792)
    text_p3 = """
Benchmark Test Page 3 - Prose & Controls (Should NOT be boxed)

Date: 2026-10-09
Website: https://example.com/api/v1/download
Section 3.2: System Architecture & Requirements
Options: pass/fail or true/false for all candidates.
Page 3 of 4
"""
    page3.insert_text((50, 50), text_p3, fontsize=12)

    # Save document
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()

    return output_path
