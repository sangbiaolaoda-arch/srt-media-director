"""html_renderer.py — 视觉 DSL → 独立可打开的 HTML 文件。"""
import os

import compiler.svg_compiler as SVGC


def render_html(spec, out_path, title="beat"):
    """写出 HTML。返回路径。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(SVGC.to_html(spec, title=title))
    return out_path


def render_svg(spec, out_path):
    """写出纯 SVG。返回路径。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(SVGC.compile_spec(spec))
    return out_path
