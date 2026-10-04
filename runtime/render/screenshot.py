"""screenshot.py — 自动选后端，把一帧（视觉 DSL）截成 PNG。

后端优先级：playwright > chromium(CLI) > cairosvg。
每一层失败都如实降级，并记录实际用到的后端（backend 字段），不假装成功。
"""
import io
import os
import subprocess
import tempfile

import compiler.svg_compiler as SVGC
from . import playwright_renderer as PW

_CAIROSVG = None
try:
    import cairosvg as _CAIROSVG
except Exception:
    _CAIROSVG = None


def backends():
    """探测可用后端（供能力探测 / 文档）。"""
    return {"playwright": PW.available(), "chromium": bool(PW.chromium_available()),
            "cairosvg": _CAIROSVG is not None}


def _via_cairosvg(spec, png_path, scale=2):
    svg = SVGC.compile_spec(spec)
    _CAIROSVG.svg2png(bytestring=svg.encode("utf-8"), write_to=png_path,
                      output_width=int(680 * scale), output_height=int(382 * scale))
    return "cairosvg"


def _via_chromium(spec, png_path, scale=2):
    chrome = PW.chromium_available()
    if not chrome:
        raise RuntimeError("no chromium")
    from render.html_renderer import render_html
    with tempfile.TemporaryDirectory() as d:
        hp = os.path.join(d, "b.html")
        render_html(spec, hp)
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--force-device-scale-factor=%d" % scale,
               "--window-size=680,382", "--screenshot=%s" % png_path, "file://" + hp]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    return "chromium"


def screenshot_spec(spec, png_path, scale=2, prefer=None):
    """把一帧截成 PNG。返回 (png_path, backend)。

    prefer: 指定首选后端（"playwright"/"chromium"/"cairosvg"），失败自动降级。
    """
    os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)
    order = [prefer] if prefer else []
    order += ["playwright", "chromium", "cairosvg"]
    seen, errors = set(), []
    for be in order:
        if not be or be in seen:
            continue
        seen.add(be)
        try:
            if be == "playwright" and PW.available():
                from render.html_renderer import render_html
                with tempfile.TemporaryDirectory() as d:
                    hp = os.path.join(d, "b.html")
                    render_html(spec, hp)
                    PW.screenshot_html(hp, png_path)
                return png_path, "playwright"
            if be == "chromium" and PW.chromium_available():
                return png_path, _via_chromium(spec, png_path, scale)
            if be == "cairosvg" and _CAIROSVG is not None:
                return png_path, _via_cairosvg(spec, png_path, scale)
        except Exception as e:
            errors.append("%s: %s" % (be, e))
    raise RuntimeError("所有渲染后端均失败: %s" % errors)
