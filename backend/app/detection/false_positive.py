"""
False Positive Filter Module
Filters out non-formula text patterns like dates, URLs, section numbers, page numbers, and ordinary prose.
"""

import re
from typing import Dict, Any

# Common non-formula patterns
DATE_PATTERN = re.compile(r'^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$')
URL_PATTERN = re.compile(r'^(https?://|www\.|ftp://|[a-zA-Z0-9\.\-]+/[a-zA-Z0-9\.\-_]+)')
SECTION_PATTERN = re.compile(r'^(Section|Chapter|Figure|Table|Page|Sect\.|Fig\.|Tab\.)\s*\d+(\.\d+)*$', re.IGNORECASE)
PAGE_NUM_PATTERN = re.compile(r'^(\d+|\d+\s*of\s*\d+|Page\s*\d+)$', re.IGNORECASE)
ORDINARY_SLASH_PATTERN = re.compile(r'^(and/or|yes/no|pass/fail|true/false|on/off|in/out|n/a|w/o|c/o)$', re.IGNORECASE)
PLAIN_TEXT_WORDS = re.compile(r'^[a-zA-Z]{3,}(\s+[a-zA-Z]{3,}){2,}$') # 3 or more plain English words without math symbols

MATH_SYMBOLS = set('+=≠±×÷≤≥∑∫√∞∈∉⊂⊆∪∩∂∇αβγδεθλμπσφψωΔΣΩ^_{}')

def is_false_positive(text: str, has_math_font: bool = False) -> bool:
    """
    Returns True if text is a false positive (not a formula).
    """
    cleaned = text.strip()
    if not cleaned:
        return True

    # Check date
    if DATE_PATTERN.match(cleaned):
        return True

    # Check URL
    if URL_PATTERN.match(cleaned):
        return True

    # Check section / figure heading
    if SECTION_PATTERN.match(cleaned):
        return True

    # Check standalone page number
    if PAGE_NUM_PATTERN.match(cleaned):
        return True

    # Check common prose slash pairs
    if ORDINARY_SLASH_PATTERN.match(cleaned):
        return True

    # If it's a multi-word plain English sentence with no math symbols or math fonts
    has_math_char = any(c in MATH_SYMBOLS for c in cleaned)
    if not has_math_char and not has_math_font:
        if PLAIN_TEXT_WORDS.match(cleaned):
            return True
        # Plain text sentence ending with period
        if cleaned.endswith('.') and not any(op in cleaned for op in ['=', '+', '-', '*', '/', '^', '√', '∫', '∑']):
            return True

    return False
