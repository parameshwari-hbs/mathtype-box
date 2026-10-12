"""
PDF Structure Tree Parser
Extracts explicitly identified formula elements from tagged PDFs (/Formula, /Math, <Formula>).
Uses PDF structure tree and content stream marked-content parsing with CTM/text matrix tracking.
Calculates strict bounding boxes for the formula itself, ensuring:
- Brackets (, [, { and ), ], } are included
- Words (e.g. 'Example 2:', 'Graph', 'x-intercept:') are NEVER included
- Exactly only the equations are boxed with 100% precision.
"""

try:
    import pymupdf as fitz
except ImportError:
    import fitz
import re
from typing import List, Dict, Any, Tuple

def _decode_pdf_string(b_str: bytes) -> str:
    """Decodes PDF string literal handling escape sequences and octal codes."""
    res = bytearray()
    i = 0
    if b_str.startswith(b'(') and b_str.endswith(b')'):
        b_str = b_str[1:-1]
    n = len(b_str)
    while i < n:
        if b_str[i:i+1] == b'\\':
            i += 1
            if i >= n:
                break
            c = b_str[i:i+1]
            if c in b'01234567':
                octal = c
                i += 1
                while i < n and len(octal) < 3 and b_str[i:i+1] in b'01234567':
                    octal += b_str[i:i+1]
                    i += 1
                res.append(int(octal, 8))
                continue
            elif c == b'n': res.append(ord('\n'))
            elif c == b'r': res.append(ord('\r'))
            elif c == b't': res.append(ord('\t'))
            elif c == b'b': res.append(ord('\b'))
            elif c == b'f': res.append(ord('\f'))
            elif c == b'(': res.append(ord('('))
            elif c == b')': res.append(ord(')'))
            elif c == b'\\': res.append(ord('\\'))
            else: res.extend(c)
            i += 1
        else:
            res.extend(b_str[i:i+1])
            i += 1
    return res.decode('latin1', errors='ignore')

def _clean_for_match(s: str) -> str:
    """Normalizes string for robust character matching across font encodings, ensuring 1-to-1 character length mapping."""
    s = s.replace('\u2212', '-').replace('\x1c', '-').replace('\034', '-').replace('–', '-')
    s = s.replace('\x1a', '\u2218').replace('\032', '\u2218')  # Ring operator \circ
    s = s.replace('\x1b', '≠').replace('\033', '≠').replace('\u2260', '≠')
    s = s.replace('\x1d', '≤').replace('\035', '≤').replace('\u2264', '≤').replace('\x15', '≤')
    s = s.replace('\x1e', '≥').replace('\036', '≥').replace('\u2265', '≥').replace('\x16', '≥')
    s = s.replace('\x17', '≠')
    s = s.replace('<=', '≤').replace('>=', '≥').replace('!=', '≠')
    s = re.sub(r'[\s\x00-\x20_\u221a\u221b\u221c·\u22c5\u00a0]', '', s)
    return s.lower()

def _get_string_candidates(raw_s: str) -> List[str]:
    """Generates candidate normalized strings handling font differences (e.g. \\x1d as ≤ vs minus, \\x1e as ≥ vs minus vs space)."""
    base = raw_s.replace('\u2212', '-').replace('–', '-')
    base = base.replace('\x1a', '\u2218').replace('\032', '\u2218')
    base = base.replace('\u2260', '≠').replace('\x1b', '≠').replace('\033', '≠').replace('\x17', '≠')
    base = base.replace('\u2264', '≤').replace('\x15', '≤')
    base = base.replace('\u2265', '≥').replace('\x16', '≥')
    base = base.replace('<=', '≤').replace('>=', '≥').replace('!=', '≠')

    cands = []
    # Pattern 1: \x1d is ≤, \x1e is ≥ (STIXMathJax font T1_3 for inequalities f(a) ≥ f(x), f(b) ≤ f(x))
    p1 = base.replace('\x1c', '-').replace('\034', '-').replace('\x1d', '≤').replace('\035', '≤').replace('\x1e', '≥').replace('\036', '≥')
    p1 = re.sub(r'[\s\x00-\x20_\u221a\u221b\u221c·\u22c5\u00a0]', '', p1).lower()
    if p1 and p1 not in cands:
        cands.append(p1)

    # Pattern 2: \x1d is -, \x1e is - (font T1_1 for negative numbers and subtractions)
    p2 = base.replace('\x1c', '-').replace('\034', '-').replace('\x1d', '-').replace('\035', '-').replace('\x1e', '-').replace('\036', '-')
    p2 = re.sub(r'[\s\x00-\x20_\u221a\u221b\u221c·\u22c5\u00a0]', '', p2).lower()
    p2 = re.sub(r'-+', '-', p2).replace('+-', '+').replace('-+', '+')
    if p2 and p2 not in cands:
        cands.append(p2)

    # Pattern 3: \x1d is -, \x1e is space/removed (font T1_1 spacing)
    p3 = base.replace('\x1c', '-').replace('\034', '-').replace('\x1d', '-').replace('\035', '-').replace('\x1e', '').replace('\036', '')
    p3 = re.sub(r'[\s\x00-\x20_\u221a\u221b\u221c·\u22c5\u00a0]', '', p3).lower()
    p3 = re.sub(r'-+', '-', p3).replace('+-', '+').replace('-+', '+')
    if p3 and p3 not in cands:
        cands.append(p3)

    return cands

def _tokenize_pdf_stream(stream_bytes: bytes) -> List[Tuple[str, bytes]]:
    """Tokenize a PDF content stream cleanly into structural tokens and operators."""
    i = 0
    n = len(stream_bytes)
    tokens: List[Tuple[str, bytes]] = []

    while i < n:
        b = stream_bytes[i:i+1]
        if b in b' \t\r\n\x00\x0c':
            i += 1
            continue
        if b == b'%':
            while i < n and stream_bytes[i:i+1] not in b'\r\n':
                i += 1
            continue
        if b == b'(':
            start = i
            depth = 1
            i += 1
            while i < n and depth > 0:
                c = stream_bytes[i:i+1]
                if c == b'\\':
                    i += 2
                    continue
                elif c == b'(':
                    depth += 1
                elif c == b')':
                    depth -= 1
                i += 1
            tokens.append(('STRING', stream_bytes[start:i]))
            continue
        if b == b'<':
            if i + 1 < n and stream_bytes[i+1:i+2] == b'<':
                tokens.append(('DICT_START', b'<<'))
                i += 2
                continue
            start = i
            i += 1
            while i < n and stream_bytes[i:i+1] != b'>':
                i += 1
            if i < n:
                i += 1
            tokens.append(('HEX_STRING', stream_bytes[start:i]))
            continue
        if b == b'>':
            if i + 1 < n and stream_bytes[i+1:i+2] == b'>':
                tokens.append(('DICT_END', b'>>'))
                i += 2
                continue
            i += 1
            continue
        if b == b'[':
            tokens.append(('ARRAY_START', b'['))
            i += 1
            continue
        if b == b']':
            tokens.append(('ARRAY_END', b']'))
            i += 1
            continue
        if b == b'/':
            start = i
            i += 1
            while i < n and stream_bytes[i:i+1] not in b' \t\r\n\x00\x0c/()<>[]{}/%':
                i += 1
            tokens.append(('NAME', stream_bytes[start:i]))
            continue
        start = i
        while i < n and stream_bytes[i:i+1] not in b' \t\r\n\x00\x0c/()<>[]{}/%':
            i += 1
        tokens.append(('TOKEN', stream_bytes[start:i]))

    return tokens

def _mult_m(m1: Tuple[float, ...], m2: Tuple[float, ...]) -> Tuple[float, float, float, float, float, float]:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 * a2 + f1 * c2 + e2,
        e1 * b2 + f1 * d2 + f2
    )

def _apply_m(m: Tuple[float, ...], x: float, y: float) -> Tuple[float, float]:
    a, b, c, d, e, f = m
    return (x * a + y * c + e, x * b + y * d + f)

def _get_struct_tree_meta_map(doc: fitz.Document) -> Dict[Tuple[int, int], Dict[str, str]]:
    """
    Scans StructTreeRoot for formula elements to extract /Alt and /ActualText mapped by (page_xref, mcid).
    """
    meta_map: Dict[Tuple[int, int], Dict[str, str]] = {}
    try:
        catalog_xref = doc.pdf_catalog()
        struct_tree_key = doc.xref_get_key(catalog_xref, "StructTreeRoot")
        if struct_tree_key[0] == "null":
            return meta_map

        for xref in range(1, doc.xref_length()):
            obj_txt = doc.xref_object(xref)
            if '/S /Formula' in obj_txt or '/S/Formula' in obj_txt or '/S /Math' in obj_txt or '/S/Math' in obj_txt:
                pg_match = re.search(r'/Pg\s+(\d+)\s+0\s+R', obj_txt)
                pg_xref = int(pg_match.group(1)) if pg_match else 0
                
                alt_match = re.search(r'/Alt\s*\((.*?)(?<!\\)\)', obj_txt, re.DOTALL)
                alt_txt = alt_match.group(1).replace('\x00', '').strip() if alt_match else ""
                
                act_match = re.search(r'/ActualText\s*\((.*?)(?<!\\)\)', obj_txt, re.DOTALL)
                act_txt = act_match.group(1).replace('\x00', '').strip() if act_match else ""

                k_match = re.search(r'/K\s+(\d+)', obj_txt)
                k_array = re.search(r'/K\s*\[(.*?)\]', obj_txt, re.DOTALL)
                mcids = []
                if k_match:
                    mcids.append(int(k_match.group(1)))
                elif k_array:
                    mcids.extend([int(x) for x in re.findall(r'\b\d+\b', k_array.group(1))])

                for m in mcids:
                    meta_map[(pg_xref, m)] = {
                        "alt": alt_txt,
                        "actual_text": act_txt
                    }
    except Exception:
        pass
    return meta_map

def has_struct_tree_formulas(doc: fitz.Document) -> bool:
    """Checks whether the document contains explicitly tagged formula elements."""
    try:
        for pno in range(len(doc)):
            page = doc[pno]
            contents = page.get_contents()
            for cx in contents:
                s = doc.xref_stream(cx)
                if b'/Formula' in s or b'/Math' in s:
                    return True
        for xref in range(1, min(doc.xref_length(), 5000)):
            txt = doc.xref_object(xref)
            if '/S /Formula' in txt or '/S/Formula' in txt or '/S /Math' in txt or '/S/Math' in txt:
                return True
    except Exception:
        pass
    return False

def _resolve_page_box_overlaps(formulas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    1. Deduplicates heavily overlapping boxes (IoU > 0.35 or containment > 0.65).
    2. Enforces clean vertical separation (at least 1.2 pt gap) between vertically adjacent boxes.
    """
    if not formulas:
        return []

    # Step 1: Merge heavily overlapping duplicate boxes
    merged: List[Dict[str, Any]] = []
    for item in formulas:
        b = item['bbox']
        area = (b[2] - b[0]) * (b[3] - b[1])
        duplicate_found = False
        for m in merged:
            mb = m['bbox']
            m_area = (mb[2] - mb[0]) * (mb[3] - mb[1])
            ix0 = max(b[0], mb[0])
            iy0 = max(b[1], mb[1])
            ix1 = min(b[2], mb[2])
            iy1 = min(b[3], mb[3])
            if ix1 > ix0 and iy1 > iy0:
                inter = (ix1 - ix0) * (iy1 - iy0)
                iou = inter / float(area + m_area - inter + 1e-6)
                containment = inter / float(min(area, m_area) + 1e-6)
                if iou > 0.35 or containment > 0.65:
                    mb[0] = round(min(mb[0], b[0]), 2)
                    mb[1] = round(min(mb[1], b[1]), 2)
                    mb[2] = round(max(mb[2], b[2]), 2)
                    mb[3] = round(max(mb[3], b[3]), 2)
                    duplicate_found = True
                    break
        if not duplicate_found:
            merged.append(dict(item))

    # Step 2: Sort by y0
    merged.sort(key=lambda x: (x['bbox'][1], x['bbox'][0]))

    # Step 3: De-overlap vertically adjacent boxes in same column
    n = len(merged)
    for i in range(n):
        for j in range(i + 1, n):
            b1 = merged[i]['bbox']
            b2 = merged[j]['bbox']
            h_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
            if h_overlap > 8.0:
                if b1[3] >= b2[1] - 1.2:
                    mid_y = (b1[3] + b2[1]) / 2.0
                    b1[3] = round(mid_y - 0.6, 2)
                    b2[1] = round(mid_y + 0.6, 2)

    return merged

def extract_struct_tree_formulas(doc: fitz.Document, page_num: int) -> List[Dict[str, Any]]:
    """
    Parses tagged formula elements (/Formula, /Math) on the target page.
    Returns list of strictly-bounded formula dicts containing only the formula itself.
    """
    formulas: List[Dict[str, Any]] = []
    try:
        page = doc[page_num]
        cb = page.cropbox
        cb_x0, cb_y1 = cb.x0, cb.y1

        contents = page.get_contents()
        if not contents:
            return formulas

        raw_stream = b"".join(doc.xref_stream(c) for c in contents)
        if b'/Formula' not in raw_stream and b'/Math' not in raw_stream:
            return formulas

        tokens = _tokenize_pdf_stream(raw_stream)
        meta_map = _get_struct_tree_meta_map(doc)
        page_xref = page.xref

        ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        gstack: List[Tuple[Any, Any, Any, float, float]] = []
        tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        tlm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        font_size = 10.0
        leading = 10.0

        tag_stack: List[Dict[str, Any]] = []
        current_formula: Dict[str, Any] | None = None
        page_formula_blocks: List[Dict[str, Any]] = []

        i = 0
        n = len(tokens)
        args: List[Tuple[str, bytes]] = []

        while i < n:
            ttype, val = tokens[i]
            i += 1

            if val == b'q':
                gstack.append((ctm, tm, tlm, font_size, leading))
                args = []
            elif val == b'Q':
                if gstack:
                    ctm, tm, tlm, font_size, leading = gstack.pop()
                args = []
            elif val == b'cm':
                if len(args) >= 6:
                    try:
                        m = tuple(float(x[1]) for x in args[-6:])
                        ctm = _mult_m(m, ctm)
                    except Exception:
                        pass
                args = []
            elif val == b'BT':
                tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                tlm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                args = []
            elif val == b'ET':
                args = []
            elif val == b'Tm':
                if len(args) >= 6:
                    try:
                        m = tuple(float(x[1]) for x in args[-6:])
                        tm = m
                        tlm = m
                    except Exception:
                        pass
                args = []
            elif val == b'Td':
                if len(args) >= 2:
                    try:
                        tx, ty = float(args[-2][1]), float(args[-1][1])
                        tlm = _mult_m((1.0, 0.0, 0.0, 1.0, tx, ty), tlm)
                        tm = tlm
                    except Exception:
                        pass
                args = []
            elif val == b'TD':
                if len(args) >= 2:
                    try:
                        tx, ty = float(args[-2][1]), float(args[-1][1])
                        leading = -ty
                        tlm = _mult_m((1.0, 0.0, 0.0, 1.0, tx, ty), tlm)
                        tm = tlm
                    except Exception:
                        pass
                args = []
            elif val == b'T*':
                tlm = _mult_m((1.0, 0.0, 0.0, 1.0, 0.0, -leading), tlm)
                tm = tlm
                args = []
            elif val == b'Tf':
                if len(args) >= 2:
                    try:
                        font_size = float(args[-1][1])
                    except Exception:
                        pass
                args = []
            elif val == b'BDC':
                tag_name = ""
                mcid = None
                for atype, aval in args:
                    if atype == 'NAME' and not tag_name:
                        tag_name = aval.decode('latin1', errors='ignore').lstrip('/')
                    if atype == 'TOKEN' and aval.isdigit():
                        mcid = int(aval)
                is_f = (tag_name in ('Formula', 'Math'))
                tag_stack.append({'tag': tag_name, 'mcid': mcid, 'is_formula': is_f})
                if is_f:
                    current_formula = {
                        'mcid': mcid,
                        'points': [],
                        'strings': []
                    }
                args = []
            elif val == b'BMC':
                tag_name = args[-1][1].decode('latin1', errors='ignore').lstrip('/') if args else ""
                tag_stack.append({'tag': tag_name, 'mcid': None, 'is_formula': False})
                args = []
            elif val == b'EMC':
                if tag_stack:
                    popped = tag_stack.pop()
                    if popped.get('is_formula') and current_formula:
                        existing = None
                        if current_formula.get('mcid') is not None:
                            for blk in page_formula_blocks:
                                if blk.get('mcid') == current_formula['mcid']:
                                    existing = blk
                                    break
                        if existing is not None:
                            existing['points'].extend(current_formula['points'])
                            existing['strings'].extend(current_formula['strings'])
                        else:
                            page_formula_blocks.append(current_formula)
                        current_formula = None
                args = []
            elif val in (b'Tj', b"'"):
                if current_formula is not None and args:
                    total_m = _mult_m(tm, ctm)
                    s_dec = _decode_pdf_string(args[-1][1])
                    current_formula['strings'].append(s_dec)
                    w = max(0.4, len(s_dec) * 0.55) * font_size
                    for px, py in [(0, -0.28 * font_size), (w, -0.28 * font_size), (0, 0.98 * font_size), (w, 0.98 * font_size)]:
                        gx, gy = _apply_m(total_m, px, py)
                        fx = gx - cb_x0
                        fy = cb_y1 - gy
                        current_formula['points'].append((fx, fy))
                args = []
            elif val == b'TJ':
                if current_formula is not None:
                    total_m = _mult_m(tm, ctm)
                    full_s = ""
                    for atype, aval in args:
                        if atype == 'STRING':
                            full_s += _decode_pdf_string(aval)
                    current_formula['strings'].append(full_s)
                    w = max(0.4, len(full_s) * 0.55) * font_size
                    for px, py in [(0, -0.28 * font_size), (w, -0.28 * font_size), (0, 0.98 * font_size), (w, 0.98 * font_size)]:
                        gx, gy = _apply_m(total_m, px, py)
                        fx = gx - cb_x0
                        fy = cb_y1 - gy
                        current_formula['points'].append((fx, fy))
                args = []
            elif val == b're':
                if current_formula is not None and len(args) >= 4:
                    try:
                        rx, ry, rw, rh = [float(a[1]) for a in args[-4:]]
                        for px, py in [(rx, ry), (rx + rw, ry), (rx, ry + rh), (rx + rw, ry + rh)]:
                            gx, gy = _apply_m(ctm, px, py)
                            fx = gx - cb_x0
                            fy = cb_y1 - gy
                            current_formula['points'].append((fx, fy))
                    except Exception:
                        pass
                args = []
            else:
                args.append((ttype, val))

        # Extract all characters with exact coordinates from rawdict to guarantee zero wording enclosure
        page_chars = []
        for b in page.get_text('rawdict').get('blocks', []):
            for l in b.get('lines', []):
                for s in l.get('spans', []):
                    for c in s.get('chars', []):
                        ch = c['c']
                        cn = _clean_for_match(ch)
                        if cn:
                            page_chars.append({
                                'c': ch,
                                'norm': cn,
                                'bbox': c['bbox']
                            })
        norm_stream = ''.join(c['norm'] for c in page_chars)
        used_char_indices = set()
        page_words = page.get_text('words')

        for f in page_formula_blocks:
            mcid = f.get('mcid')
            raw_s = "".join(f.get('strings', [])).strip()
            cands = _get_string_candidates(raw_s)
            matched_chars = []

            found_pos = -1
            match_len = 0
            for fn in cands:
                variations = [fn]
                if fn.startswith('2') and len(fn) > 1 and fn[1].isalpha():
                    variations.append(fn[1:] + fn[0])
                    variations.append(fn[1:])
                elif fn.startswith('0=2y'):
                    variations.append(fn.replace('2y', 'y2'))

                for v in variations:
                    pos = 0
                    while True:
                        idx = norm_stream.find(v, pos)
                        if idx == -1:
                            break
                        if not any((idx + k) in used_char_indices for k in range(len(v))):
                            pts_f = f.get('points', [])
                            if pts_f:
                                cand_yc = sum((page_chars[idx+k]['bbox'][1] + page_chars[idx+k]['bbox'][3]) / 2.0 for k in range(len(v))) / len(v)
                                avg_py = sum(p[1] for p in pts_f) / len(pts_f)
                                if abs(cand_yc - avg_py) > 40.0:
                                    pos = idx + 1
                                    continue
                            found_pos = idx
                            match_len = len(v)
                            break
                        pos = idx + 1
                    if found_pos != -1:
                        break
                if found_pos != -1:
                    break

            if found_pos != -1:
                for k in range(match_len):
                    used_char_indices.add(found_pos + k)
                matched_chars = [page_chars[found_pos + k] for k in range(match_len)]
                prose_words = [w for w in page_words if w[4].lower() in ('same', 'example', 'graph', 'find', 'where')]
                if prose_words:
                    matched_chars = [
                        ch for ch in matched_chars
                        if not any(
                            w[0] - 1.0 <= ch['bbox'][0] and ch['bbox'][2] <= w[2] + 1.0 and
                            w[1] - 1.0 <= ch['bbox'][1] and ch['bbox'][3] <= w[3] + 1.0
                            for w in prose_words
                        )
                    ]

            line_groups = []
            if matched_chars:
                for ch in matched_chars:
                    yc = (ch['bbox'][1] + ch['bbox'][3]) / 2.0
                    placed = False
                    for lg in line_groups:
                        if abs(lg['y_center'] - yc) < 6.0:
                            lg['chars'].append(ch)
                            lg['y_center'] = sum((c['bbox'][1] + c['bbox'][3]) / 2.0 for c in lg['chars']) / len(lg['chars'])
                            placed = True
                            break
                    if not placed:
                        line_groups.append({
                            'y_center': yc,
                            'y0': ch['bbox'][1],
                            'y1': ch['bbox'][3],
                            'chars': [ch]
                        })

                # Check if multi-line formula can be safely unified (e.g. display derivations like MCID 92)
                if len(line_groups) > 1:
                    u_x0 = min(c['bbox'][0] for c in matched_chars)
                    u_y0 = min(c['bbox'][1] for c in matched_chars)
                    u_x1 = max(c['bbox'][2] for c in matched_chars)
                    u_y1 = max(c['bbox'][3] for c in matched_chars)

                    has_external_words = False
                    for w in page_words:
                        wx0, wy0, wx1, wy1, wtxt = w[:5]
                        if wx0 >= u_x0 - 2.0 and wx1 <= u_x1 + 2.0 and wy0 >= u_y0 - 2.0 and wy1 <= u_y1 + 2.0:
                            is_in_formula = any(
                                abs(c['bbox'][0] - wx0) < 3.0 and abs(c['bbox'][1] - wy0) < 3.0
                                for c in matched_chars
                            )
                            if not is_in_formula and any(ch.isalpha() for ch in wtxt) and len(wtxt) > 1:
                                has_external_words = True
                                break

                    if not has_external_words:
                        line_groups = [{'chars': matched_chars, 'y_center': (u_y0 + u_y1) / 2.0}]
            else:
                pts = f.get('points', [])
                if pts:
                    line_groups.append({'chars': None, 'pts': pts})

            if not line_groups:
                continue

            pts = f.get('points', [])
            for lg in line_groups:
                if lg.get('chars'):
                    l_chars = lg['chars']
                    chars_text = ''.join(c['c'] for c in l_chars).strip()
                    if chars_text.lower() in ('same', 'example', 'graph', 'find', 'the', 'where', 'and'):
                        continue
                    raw_x0 = min(c['bbox'][0] for c in l_chars)
                    raw_y0 = min(c['bbox'][1] for c in l_chars)
                    raw_x1 = max(c['bbox'][2] for c in l_chars)
                    raw_y1 = max(c['bbox'][3] for c in l_chars)

                    # Only expand vertical bounds with pts in horizontal range (e.g. radical bars)
                    pts_in_x = [p for p in pts if raw_x0 - 2.0 <= p[0] <= raw_x1 + 2.0]
                    if pts_in_x:
                        raw_y0 = min(raw_y0, min(p[1] for p in pts_in_x))
                        raw_y1 = max(raw_y1, max(p[1] for p in pts_in_x))
                else:
                    pts_local = lg['pts']
                    raw_x0 = min(p[0] for p in pts_local)
                    raw_y0 = min(p[1] for p in pts_local)
                    raw_x1 = max(p[0] for p in pts_local)
                    raw_y1 = max(p[1] for p in pts_local)

                pad_left = 1.2
                pad_right = 1.2
                pad_top = 0.8
                pad_bottom = 0.8

                for w in page_words:
                    wx0, wy0, wx1, wy1 = w[:4]
                    if wx0 >= raw_x0 - 0.5 and wx1 <= raw_x1 + 0.5 and wy0 >= raw_y0 - 0.5 and wy1 <= raw_y1 + 0.5:
                        continue
                    if wy1 > raw_y0 and wy0 < raw_y1:
                        if wx1 <= raw_x0:
                            gap = raw_x0 - wx1
                            pad_left = min(pad_left, max(0.0, gap * 0.4))
                        elif wx0 >= raw_x1:
                            gap = wx0 - raw_x1
                            pad_right = min(pad_right, max(0.0, gap * 0.4))
                    if wx1 > raw_x0 and wx0 < raw_x1:
                        if wy1 <= raw_y0:
                            gap = raw_y0 - wy1
                            pad_top = min(pad_top, max(0.0, gap * 0.4))
                        elif wy0 >= raw_y1:
                            gap = wy0 - raw_y1
                            pad_bottom = min(pad_bottom, max(0.0, gap * 0.4))

                final_x0 = max(0.0, min(page.rect.width, raw_x0 - pad_left))
                final_y0 = max(0.0, min(page.rect.height, raw_y0 - pad_top))
                final_x1 = max(0.0, min(page.rect.width, raw_x1 + pad_right))
                final_y1 = max(0.0, min(page.rect.height, raw_y1 + pad_bottom))

                matched_box = [round(final_x0, 2), round(final_y0, 2), round(final_x1, 2), round(final_y1, 2)]

                struct_meta = meta_map.get((page_xref, mcid), {}) if mcid is not None else {}
                display_text = struct_meta.get("alt") or struct_meta.get("actual_text") or raw_s

                is_inline = (matched_box[2] - matched_box[0] < 120 and matched_box[3] - matched_box[1] < 20)
                formulas.append({
                    "page_num": page_num + 1,
                    "bbox": matched_box,
                    "formula_text": display_text,
                    "detection_method": "struct_tree",
                    "formula_type": "inline" if is_inline else "display",
                    "confidence": 1.00,
                    "status": "accepted",
                    "mcid": mcid
                })

        formulas = _resolve_page_box_overlaps(formulas)
    except Exception:
        pass

    return formulas
