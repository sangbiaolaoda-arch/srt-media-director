"""svg_compiler.py — 视觉 DSL → SVG / HTML。

把「可分离图层」（每元素一个整幅 SVG + 包围盒）合成一张整幅 SVG；
再包成可独立打开的 HTML，供浏览器 / Playwright / chromium 截帧。
"""
import ref_frame as R


def _inner(svg):
    """取单个元素 SVG 的内容（去掉外层 <svg> 包装）。"""
    s = (svg or "").strip()
    if s.startswith("<svg"):
        s = s[s.index(">") + 1:]
        if s.endswith("</svg>"):
            s = s[:-len("</svg>")]
    return s


def compile_element(el):
    """单元素 → SVG 片段（供调试）。"""
    return el["svg"]


def compile_spec(spec, width=None, height=None):
    """视觉 DSL → 一张整幅 SVG 字符串。"""
    w = width or R.CANVAS_W
    h = height or R.CANVAS_H
    bg = spec.get("bg", R.BG)
    parts = ['<rect width="%d" height="%d" rx="8" fill="%s"/>' % (R.CANVAS_W, R.CANVAS_H, bg)]
    for el in spec["elements"]:
        parts.append(_inner(el["svg"]))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d">%s</svg>' % (w, h, R.CANVAS_W, R.CANVAS_H, "".join(parts)))


def to_html(spec, title="beat", width=None, height=None):
    """视觉 DSL → 可独立打开的 HTML（内嵌整幅 SVG）。"""
    svg = compile_spec(spec, width, height)
    return ("<!doctype html><html><head><meta charset='utf-8'><title>%s</title>"
            "<style>html,body{margin:0;padding:0;background:#fff}"
            "svg{display:block}</style></head><body>%s</body></html>" % (title, svg))
