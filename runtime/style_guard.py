"""Stage 6 — 风格锁定扫描（v6.0）。

读取 runtime/style_tokens.json，扫描生成的 HTML 与 SVG，凡出现 token 之外的
颜色 / 字体 / 线宽即报错。这样风格一致性是机器保证的，不靠提示。
"""
import json
import os
import re

_HEX = re.compile(r"#([0-9a-fA-F]{6})")
_RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
_FONT = re.compile(r"font-family\s*[:=]\s*['\"]?([A-Za-z\u4e00-\u9fff ,'-]+)")
_STROKE_W = re.compile(r"stroke-width\s*[:=]\s*['\"]?([0-9.]+)")


def _norm_hex(h):
    return "#" + h.upper()


def load_tokens(root):
    with open(os.path.join(root, "runtime", "style_tokens.json"), encoding="utf-8") as f:
        return json.load(f)


def scan(root, html_path, svg_paths=None):
    """返回 audit dict：列出 token 之外的颜色 / 线宽 / 字体。"""
    tok = load_tokens(root)
    allowed_colors = set()
    for k in ("background", "ink", "muted", "accent", "rose_fill", "rose_edge",
              "diagram", "diagram_green"):
        if tok.get(k):
            allowed_colors.add(_norm_hex(tok[k].lstrip("#")))
    for c in tok.get("palette", []):
        allowed_colors.add(_norm_hex(c.lstrip("#")))
    for c in tok.get("allowed_neutral", []):
        allowed_colors.add(_norm_hex(c.lstrip("#")))
    allowed_w = set(str(x) for x in tok.get("line_widths", []))
    allowed_fonts = set(tok.get("fonts", []))

    issues = []
    files = []
    if html_path and os.path.exists(html_path):
        files.append(html_path)
    for p in (svg_paths or []):
        if os.path.exists(p):
            files.append(p)
    if os.path.isdir(html_path or ""):
        for dp, _, fns in os.walk(html_path):
            for fn in fns:
                if fn.lower().endswith((".svg", ".html")):
                    files.append(os.path.join(dp, fn))

    for fp in files:
        try:
            with open(fp, encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        except Exception:
            continue
        for m in _HEX.finditer(txt):
            col = _norm_hex(m.group(1))
            if col not in allowed_colors and not _is_transparentish(txt, m.start()):
                issues.append(_iss("STYLE_COLOR", fp, "token 外颜色 %s" % col))
        for m in _STROKE_W.finditer(txt):
            w = m.group(1).rstrip("0").rstrip(".") or "0"
            if w not in allowed_w and str(float(w)) not in {str(float(x)) for x in allowed_w}:
                issues.append(_iss("STYLE_STROKE", fp, "token 外线宽 %s" % m.group(1)))
        for m in _FONT.finditer(txt):
            fam = m.group(1).lower()
            if not any(a in fam for a in allowed_fonts):
                issues.append(_iss("STYLE_FONT", fp, "token 外字体 %s" % m.group(1).strip()[:40]))

    uniq = {}
    for i in issues:
        uniq[(i["code"], i["msg"])] = i
    issues = list(uniq.values())
    return {"status": "PASS" if not issues else "FAIL",
            "scanned_files": files, "issues": issues}


def _is_transparentish(txt, pos):
    # 允许 #FFFFFF/#000000 之外的透明占位（如 SVG 里 fill="none" 不会命中 hex）
    return False


def _iss(code, fp, msg):
    return {"severity": "err", "layer": "style", "code": code,
            "file": os.path.basename(fp), "msg": msg}
