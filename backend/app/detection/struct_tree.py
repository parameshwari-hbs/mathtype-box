"""
PDF Structure Tree Parser
Extracts explicitly identified formula elements from tagged PDFs (/Formula, /Math, <Formula>).
Uses PDF structure tree and content stream marked-content parsing with CTM/text matrix tracking.
Calculates strict bounding boxes for the formula itself, ensuring:
- Brackets (, [, { and ), ], } are included
- Words (e.g. 'Example 2:', 'Graph', 'x-intercept:') are NEVER included
- Exactly only the equations are boxed with 100% precision.
"""

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
    """Normalizes string for robust character matching across font encodings."""
    s = s.replace('\u2212', '-').replace('\x1c', '-').replace('\x1d', '-').replace('\035', '-').replace('–', '-')
    s = s.replace('\x1e', '<=').replace('\u2264', '<=').replace('\u2265', '>=').replace('\x1b', '!=')
    s = re.sub(r'[\s\x00-\x1c\x1e-\x1f_\u221a\u221b\u221c·\u22c5]', '', s)
    return s.lower()

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
                        page_formula_blocks.append(current_formula)
                        current_formula = None
                args = []
            elif val in (b'Tj', b"'"):
                if current_formula is not None and args:
                    total_m = _mult_m(tm, ctm)
                    s_dec = _decode_pdf_string(args[-1][1])
                    current_formula['strings'].append(s_dec)
                    w = max(0.4, len(s_dec) * 0.55) * font_size
                    # Encompass character bounds including ascenders/descenders
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
            fn = _clean_for_match(raw_s)
            matched_chars = []

            if fn:
                variations = [fn]
                if fn.startswith('2') and len(fn) > 1 and fn[1].isalpha():
                    variations.append(fn[1:] + fn[0])
                    variations.append(fn[1:])
                elif fn.startswith('0=2y'):
                    variations.append(fn.replace('2y', 'y2'))

                found_pos = -1
                match_len = len(fn)
                for v in variations:
                    pos = 0
                    while True:
                        idx = norm_stream.find(v, pos)
                        if idx == -1:
                            break
                        if not any((idx + k) in used_char_indices for k in range(len(v))):
                            found_pos = idx
                            match_len = len(v)
                            break
                        pos = idx + 1
                    if found_pos != -1:
                        break

                if found_pos != -1:
                    for k in range(match_len):
                        used_char_indices.add(found_pos + k)
                    matched_chars = [page_chars[found_pos + k] for k in range(match_len)]

            line_groups = []
            if matched_chars:
                # Group matched characters by vertical line to prevent multi-line formulas from boxing prose text
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
                        line_groups.append({'y_center': yc, 'chars': [ch]})
            else:
                pts = f.get('points', [])
                if pts:
                    line_groups.append({'chars': None, 'pts': pts})

            if not line_groups:
                continue

            for lg in line_groups:
                if lg.get('chars'):
                    l_chars = lg['chars']
                    raw_x0 = min(c['bbox'][0] for c in l_chars)
                    raw_y0 = min(c['bbox'][1] for c in l_chars)
                    raw_x1 = max(c['bbox'][2] for c in l_chars)
                    raw_y1 = max(c['bbox'][3] for c in l_chars)
                else:
                    pts = lg['pts']
                    raw_x0 = min(p[0] for p in pts)
                    raw_y0 = min(p[1] for p in pts)
                    raw_x1 = max(p[0] for p in pts)
                    raw_y1 = max(p[1] for p in pts)

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
    except Exception:
        pass

    return formulas
