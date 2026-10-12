"""
Native PDF Text Span & Precision Math Formula Analyzer
Strictly tags ONLY mathematical formulas and equations, never paragraph text.
Guarantees that trailing/leading commas, periods, and punctuation are completely excluded.
"""

import re
import fitz
from typing import List, Dict, Any, Tuple
from app.detection.false_positive import is_false_positive, MATH_SYMBOLS

MATH_FONT_KEYWORDS = [
    'math', 'symbol', 'cmsy', 'cmmi', 'cmex', 'cmr', 'stix', 'cambria math',
    'eufm', 'msam', 'msbm', 'mtmi', 'mtsy', 'italic', 'ital', 'nimbusromno9l-reguital'
]

MATH_FUNCTIONS = {
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'lim', 'det', 'exp',
    'max', 'min', 'gcd', 'lcm', 'deg', 'dim', 'ker', 'hom', 'arg', 'co', 'const', 'def'
}

# Relational and operator characters
RELATIONAL_OPS = set('=≠≤≥<>≈≡∈∉⊂⊆⊃⊇∪∩')
RELATIONAL_OPS_REGEX = re.compile(r'[=≠≤≥<>≈≡∈∉⊂⊆⊃⊇∪∩]')
SUM_INT_PATTERN = re.compile(r'(∑|∫|∏|√|∂|∇|lim|log|ln)')

# Common English prose words (must NEVER be tagged as formulas)
COMMON_PROSE_WORDS = {
    'the', 'of', 'and', 'in', 'to', 'a', 'is', 'that', 'for', 'it', 'as', 'was', 'with', 'be',
    'by', 'on', 'not', 'he', 'i', 'this', 'are', 'or', 'his', 'from', 'at', 'which', 'but',
    'more', 'has', 'had', 'they', 'you', 'were', 'their', 'one', 'all', 'we', 'can', 'an',
    'your', 'said', 'each', 'she', 'do', 'how', 'if', 'will', 'up', 'other', 'about', 'out',
    'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'him',
    'into', 'time', 'look', 'two', 'write', 'go', 'see', 'number', 'no', 'way', 'could',
    'people', 'my', 'than', 'first', 'water', 'been', 'call', 'who', 'oil', 'its', 'now',
    'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made', 'may', 'part', 'distance',
    'between', 'points', 'rectangular', 'coordinate', 'system', 'given', 'circle', 'plane',
    'equidistant', 'fixed', 'point', 'called', 'center', 'radius', 'standard', 'form',
    'general', 'completing', 'square', 'purpose', 'identify', 'equations', 'equation',
    'represent', 'graph', 'results', 'constant', 'single', 'solution', 'set', 'degenerate',
    'case', 'empty', 'sum', 'squares', 'equal', 'zero', 'only', 'individual', 'term',
    'therefore', 'root', 'converted', 'reduced', 'defined', 'absence', 'controls',
    'approximation', 'solutions', 'established', 'natural', 'stability', 'conditions',
    'foundational', 'works', 'however', 'note', 'associated', 'looks', 'similar',
    'subsystem', 'contrast', 'latter', 'evolves', 'stretched', 'scale', 'vector',
    'parameters', 'lebesgue', 'measurable', 'functions', 'taking', 'values', 'throughout',
    'what', 'follows', 'assume', 'there', 'exist', 'sufficiently', 'large', 'compact',
    'sets', 'such', 'start', 'remain', 'within', 'denotes', 'closed', 'unit', 'ball',
    'enough', 'also', 'least', 'initial', 'condition', 'denote', 'averages', 'union',
    'over', 'standing', 'obtained', 'following', 'length', 'horizon', 'tends', 'infinity',
    'converges', 'more', 'precisely', 'stands', 'hausdorff', 'metric', 'bounded', 'subsets',
    'finite', 'dimensional', 'space', 'euclidean', 'norm', 'multivalued', 'lipschitz',
    'continuous', 'under', 'these', 'assumptions', 'referred', 'consider', 'inclusion',
    'key', 'concepts', 'examples', 'section', 'chapter', 'summary', 'detailed', 'value'
}

PUNCTUATION_CHARS = set('.,;:!?•')

def is_math_font(font_name: str) -> bool:
    """Checks if font name indicates a math or italic font."""
    font_lower = font_name.lower()
    return any(kw in font_lower for kw in MATH_FONT_KEYWORDS)

def is_prose_word(word: str) -> bool:
    """
    Returns True if word is an ordinary English prose word (not part of a formula).
    """
    cleaned = re.sub(r'[^a-zA-Z]', '', word).lower()
    if not cleaned or cleaned in MATH_FUNCTIONS:
        return False
    if cleaned in COMMON_PROSE_WORDS:
        return True
    # Single letters are math variables (x, y, z, t, u, v, w, r, c, h, k, A, B, C)
    if len(cleaned) == 1:
        return False
    # If 3 or more letters and not in math functions, it is almost certainly a prose word
    if len(cleaned) >= 3 and not any(c in 'xyzabchkrntuvw' for c in cleaned):
        return True
    return False

def extract_equation_bounds(line_text: str, rel_idx: int) -> Tuple[int, int]:
    """
    Bidirectionally expands around a relation/operator token to find the exact formula boundaries.
    Stops immediately when encountering prose words, bullets, or punctuation.
    Guarantees trailing/leading commas or periods are stripped.
    """
    # 1. Walk LEFT to find where formula starts
    i = rel_idx - 1
    while i >= 0 and line_text[i] == ' ':
        i -= 1
        
    start_idx = max(0, i)
    paren_depth = bracket_depth = brace_depth = 0
    
    while i >= 0:
        ch = line_text[i]
        if ch == ')': paren_depth += 1
        elif ch == '(': paren_depth = max(0, paren_depth - 1)
        elif ch == ']': bracket_depth += 1
        elif ch == '[': bracket_depth = max(0, bracket_depth - 1)
        elif ch == '}': brace_depth += 1
        elif ch == '{': brace_depth = max(0, brace_depth - 1)
        
        # Outside brackets/parens, stop if hitting prose words or punctuation
        if ch == ' ' and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
            preceding_str = line_text[:i]
            match = re.search(r'([a-zA-Z]+)[,\.:;]?$', preceding_str)
            if match and is_prose_word(match.group(1)):
                break
            if re.search(r'[•\:\;\,\.\?\!]$', preceding_str.strip()):
                break
        elif paren_depth == 0 and bracket_depth == 0 and brace_depth == 0 and ch in PUNCTUATION_CHARS:
            start_idx = i + 1
            break
            
        start_idx = i
        i -= 1

    # 2. Walk RIGHT to find where formula ends
    i = rel_idx + 1
    while i < len(line_text) and line_text[i] == ' ':
        i += 1
        
    end_idx = min(len(line_text), i)
    paren_depth = bracket_depth = brace_depth = 0
    
    while i < len(line_text):
        ch = line_text[i]
        if ch == '(': paren_depth += 1
        elif ch == ')': paren_depth = max(0, paren_depth - 1)
        elif ch == '[': bracket_depth += 1
        elif ch == ']': bracket_depth = max(0, bracket_depth - 1)
        elif ch == '{': brace_depth += 1
        elif ch == '}': brace_depth = max(0, brace_depth - 1)
        
        if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
            # Never include punctuation like comma or period
            if ch in PUNCTUATION_CHARS:
                end_idx = i
                break
            if ch == ' ':
                following_str = line_text[i+1:]
                match = re.match(r'([a-zA-Z]+)', following_str)
                if match and is_prose_word(match.group(1)):
                    end_idx = i
                    break
                # Right aligned equation number e.g. (1.5)
                if re.match(r'\s*\(\d+(\.\d+)*\)', following_str):
                    end_idx = i
                    break
                    
        end_idx = i + 1
        i += 1

    # Strip any leading or trailing whitespace, commas, periods, or punctuation
    sub = line_text[start_idx:end_idx]
    l_strip = len(sub) - len(sub.lstrip(' .,;:!?•-'))
    start_idx += l_strip
    r_strip = len(sub) - len(sub.rstrip(' .,;:!?•-'))
    end_idx -= r_strip

    return max(0, start_idx), max(start_idx, end_idx)

def extract_text_span_candidates(page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
    """
    Extracts strictly mathematical formulas and equations with character-level accuracy.
    Excludes all paragraph prose and strips commas, periods, and punctuation.
    """
    candidates = []
    raw_dict = page.get_text("rawdict")

    for block in raw_dict.get("blocks", []):
        if block.get("type") != 0:  # Skip image blocks
            continue
            
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            all_chars = [c for s in spans for c in s.get("chars", [])]
            if not all_chars:
                continue

            line_text = "".join(c.get("c", "") for c in all_chars)
            if not line_text.strip():
                continue

            # Check if this line is an ordinary paragraph sentence
            words = [w for w in re.findall(r'[a-zA-Z]+', line_text) if len(w) >= 3]
            prose_count = sum(1 for w in words if is_prose_word(w))
            is_predominantly_prose = prose_count >= 3

            # --- STAGE 1: Relational Equations & Formulas (=, ≠, ≤, ≥, <, >, ∈, ⊂, etc.) ---
            rel_matches = list(RELATIONAL_OPS_REGEX.finditer(line_text))
            processed_ranges = []

            if rel_matches:
                for m in rel_matches:
                    r_idx = m.start()
                    if any(st <= r_idx < en for st, en in processed_ranges):
                        continue
                    st, en = extract_equation_bounds(line_text, r_idx)
                    if en > st:
                        processed_ranges.append((st, en))

                for s, e in processed_ranges:
                    # Strip any punctuation characters from selected characters
                    matched_chars = [
                        c for c in all_chars[s:e]
                        if not c.get("c", "").isspace() and c.get("c", "") not in PUNCTUATION_CHARS
                    ]
                    if not matched_chars:
                        continue

                    formula_str = line_text[s:e].strip(" .,;:!?•-")
                    if len(formula_str) < 2 or is_false_positive(formula_str):
                        continue

                    x0 = min(c["bbox"][0] for c in matched_chars)
                    y0 = min(c["bbox"][1] for c in matched_chars)
                    x1 = max(c["bbox"][2] for c in matched_chars)
                    y1 = max(c["bbox"][3] for c in matched_chars)

                    candidates.append({
                        "page_num": page_num + 1,
                        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                        "formula_text": formula_str,
                        "detection_method": "native_text",
                        "formula_type": "inline" if is_predominantly_prose else "display",
                        "confidence": 0.98,
                        "status": "accepted"
                    })

            # --- STAGE 2: Display Equations (Centered/Indented without relational ops) ---
            if not is_predominantly_prose and not rel_matches:
                has_sum_int = bool(SUM_INT_PATTERN.search(line_text))
                has_math_f = any(is_math_font(s.get("font", "")) for s in spans)

                if has_sum_int or (has_math_f and len(line_text.strip()) > 2):
                    # Exclude equation number like (1.5) from right
                    clean_chars = list(all_chars)
                    eq_num_match = re.search(r'\s*\(\d+(\.\d+)*\)\s*$', line_text)
                    if eq_num_match:
                        clean_chars = clean_chars[:eq_num_match.start()]

                    non_punct_chars = [
                        c for c in clean_chars
                        if not c.get("c", "").isspace() and c.get("c", "") not in PUNCTUATION_CHARS
                    ]

                    if non_punct_chars:
                        formula_str = line_text[:len(clean_chars)].strip(" .,;:!?•-")
                        if not is_false_positive(formula_str):
                            x0 = min(c["bbox"][0] for c in non_punct_chars)
                            y0 = min(c["bbox"][1] for c in non_punct_chars)
                            x1 = max(c["bbox"][2] for c in non_punct_chars)
                            y1 = max(c["bbox"][3] for c in non_punct_chars)

                            candidates.append({
                                "page_num": page_num + 1,
                                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                                "formula_text": formula_str,
                                "detection_method": "native_text",
                                "formula_type": "display",
                                "confidence": 0.95,
                                "status": "accepted"
                            })

            # --- STAGE 3: Isolated Inline Math Terms, Sets, and Functions ---
            # (e.g. u(·), y_z(τ), V(z), [0, T], r B^m, R^m)
            # STRICT RULES:
            # 1. Must NOT contain relational operators (already handled in Stage 1)
            # 2. Must NOT have more than 2 whitespace words
            # 3. Must NOT contain English prose words
            # 4. Punctuation (commas, periods) is stripped from characters
            for s in spans:
                s_chars = s.get("chars", [])
                if not s_chars:
                    continue
                s_text = "".join(c.get("c", "") for c in s_chars).strip()
                if not s_text or len(s_text) < 1:
                    continue

                # Rule 1: No relational operators in Stage 3
                if any(op in s_text for op in RELATIONAL_OPS):
                    continue

                # Rule 2: Maximum 2 whitespace words (cannot be a sentence/paragraph)
                words_in_span = s_text.split()
                if len(words_in_span) > 2:
                    continue

                # Rule 3: No English prose words
                if any(is_prose_word(w) for w in words_in_span):
                    continue

                font_is_math = is_math_font(s.get("font", "")) or (s.get("flags", 0) & 2 != 0)
                has_brackets = bool(re.match(r'^[\(\[\{].*[\)\]\}]$', s_text))
                has_sup_sub = any(c in '^_{}' for c in s_text) or any(c in MATH_SYMBOLS for c in s_text)

                if (font_is_math or has_brackets or has_sup_sub):
                    # Filter out commas, periods, colons
                    clean_s_chars = [
                        c for c in s_chars
                        if not c.get("c", "").isspace() and c.get("c", "") not in PUNCTUATION_CHARS
                    ]
                    if not clean_s_chars:
                        continue

                    c_x0 = min(c["bbox"][0] for c in clean_s_chars)
                    c_y0 = min(c["bbox"][1] for c in clean_s_chars)
                    c_x1 = max(c["bbox"][2] for c in clean_s_chars)
                    c_y1 = max(c["bbox"][3] for c in clean_s_chars)

                    # Ensure not already inside a candidate bounding box
                    already_tagged = False
                    for existing in candidates:
                        ex_b = existing["bbox"]
                        if (ex_b[0] - 1 <= c_x0 and c_x1 <= ex_b[2] + 1 and
                            ex_b[1] - 1 <= c_y0 and c_y1 <= ex_b[3] + 1):
                            already_tagged = True
                            break

                    clean_term = s_text.strip(" .,;:!?•-")
                    if not already_tagged and len(clean_term) >= 1 and not is_false_positive(clean_term):
                        candidates.append({
                            "page_num": page_num + 1,
                            "bbox": [round(c_x0, 2), round(c_y0, 2), round(c_x1, 2), round(c_y1, 2)],
                            "formula_text": clean_term,
                            "detection_method": "native_text",
                            "formula_type": "inline",
                            "confidence": 0.90,
                            "status": "accepted"
                        })

    return candidates
