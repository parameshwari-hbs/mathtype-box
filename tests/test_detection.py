"""
FormulaBox Automator - Unit & Integration Test Suite
"""

import os
import unittest
import fitz

import sys
sys.path.insert(0, os.path.abspath("backend"))

from app.config import AnnotationConfig
from app.validation.test_generator import generate_sample_test_pdf
from app.detection.hybrid_engine import run_hybrid_formula_detection
from app.pdf_processor.annotator import apply_annotations_to_document
from app.pdf_processor.validator import check_pdf_security, validate_exported_pdf
from app.pdf_processor.preservation import deduplicate_detections

class TestFormulaBoxAutomator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath("temp_tests")
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.pdf_path = os.path.join(cls.test_dir, "sample_test.pdf")
        generate_sample_test_pdf(cls.pdf_path)

    def test_01_pdf_security_validation(self):
        res = check_pdf_security(self.pdf_path)
        self.assertTrue(res["valid"])
        self.assertFalse(res["is_encrypted"])
        self.assertGreater(res["page_count"], 0)

    def test_02_formula_detection(self):
        doc = fitz.open(self.pdf_path)
        formulas = run_hybrid_formula_detection(doc)
        doc.close()
        
        self.assertGreater(len(formulas), 0, "Should detect formulas in benchmark PDF")
        for f in formulas:
            self.assertIn("bbox", f)
            self.assertIn("confidence", f)
            self.assertIn("status", f)
            self.assertIn("detection_method", f)

    def test_03_pdf_annotation_and_001pt_requirement(self):
        doc = fitz.open(self.pdf_path)
        formulas = run_hybrid_formula_detection(doc)
        config = AnnotationConfig(border_width=0.01, border_color="#E31B23")
        
        applied_count, results = apply_annotations_to_document(doc, formulas, config)
        output_path = os.path.join(self.test_dir, "annotated_out.pdf")
        doc.save(output_path)
        doc.close()

        val_res = validate_exported_pdf(output_path, 3, applied_count)
        self.assertTrue(val_res["success"])
        self.assertEqual(val_res["annotations_count"], applied_count)

    def test_04_preservation_and_deduplication(self):
        doc = fitz.open(self.pdf_path)
        page = doc[0]
        dummy_boxes = [{"bbox": [100, 100, 200, 150], "status": "accepted"}]
        fresh, dups = deduplicate_detections(page, dummy_boxes)
        doc.close()
        self.assertEqual(len(fresh), 1)

    def test_05_tight_formula_cropping_without_prose(self):
        doc = fitz.open()
        p = doc.new_page(width=612, height=792)
        p.insert_text((50, 50), 'results in an equation of the form (x - h)^2 + (y - k)^2 = c', fontsize=10)
        p.insert_text((50, 70), 'individual term is zero. Therefore, x = 4 and y = -1.', fontsize=10)
        p.insert_text((50, 90), '• If c = 0, then the graph will be a single point.', fontsize=10)
        
        formulas = run_hybrid_formula_detection(doc)
        doc.close()

        texts = [f["formula_text"] for f in formulas]
        # Verify formulas are tightly extracted without English sentences
        self.assertIn('(x - h)^2 + (y - k)^2 = c', texts)
        self.assertIn('c = 0', texts)
        self.assertTrue(any('x = 4' in t for t in texts))
        
        # Verify bbox of (x - h)^2 starts far past 'results in an equation of the form' (which starts at x=50)
        eq1 = next(f for f in formulas if f["formula_text"] == '(x - h)^2 + (y - k)^2 = c')
        self.assertGreater(eq1["bbox"][0], 150.0, "Bounding box must not include preceding English words")

    def test_06_tagged_pdf_formula_only_detection(self):
        uploads_dir = os.path.abspath("temp_uploads")
        if os.path.exists(uploads_dir):
            pdfs = [f for f in os.listdir(uploads_dir) if "a11y" in f.lower() and f.lower().endswith(".pdf")]
            if pdfs:
                sample_pdf = os.path.join(uploads_dir, pdfs[0])
                doc = fitz.open(sample_pdf)
                from app.detection.struct_tree import has_struct_tree_formulas
                self.assertTrue(has_struct_tree_formulas(doc), "Document should be detected as tagged PDF")
                formulas = run_hybrid_formula_detection(doc, only_tagged=True)
                doc.close()

                self.assertGreater(len(formulas), 50, "Should detect tagged formulas across document")
                for f in formulas:
                    self.assertEqual(f["detection_method"], "struct_tree", "Method must be struct_tree only")
                    self.assertEqual(f["confidence"], 1.00, "Confidence should be 1.00")
                    self.assertEqual(f["status"], "accepted")

if __name__ == "__main__":
    unittest.main()
