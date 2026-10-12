"""render_gallery.py — render the layout library as SVG contact sheets.

Additive capability surface. It draws one card per composition blueprint so the
110 blueprints can be previewed in the browser without a renderer: rounded box =
region slot, corner badge = reading order, top-left label = blueprint id / family.

It is pure-stdlib (no Pillow, no cairosvg) — it only emits SVG text, so it runs
anywhere Python runs:

    cd runtime
    python -m capability_library.render_gallery --out ../examples/layout-gallery

Emitted files:
    overview.svg  — 25 representative blueprints
    text.svg      — every text blueprint   (42)
    image.svg     — every image blueprint  (34)
    chart.svg     — every chart blueprint  (34)

The card geometry is deterministic; re-running produces byte-identical output.
"""
from __future__ import annotations

import argparse
import os

from . import layout_library as _L

# ------------------------------------------------------------------ geometry
CARD_W, CARD_H = 220.0, 150.0
CARD_PAD = 12.0
INNER_PAD = 10.0        # inner canvas inset inside the card
GAP = 18.0
COLS = 5
HEADER = 46.0           # top band holding the sheet title

_FAMILY_COLOR = {
    "text": "#5694ff",
    "image": "#4fd39a",
    "chart": "#f0a35e",
}
_INK = "#e6ebf5"
_MUTED = "#9aa6bd"
_CANVAS = "#181c28"
_BG = "#0f121a"


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _card(layout: dict, ox: float, oy: float) -> str:
    """Return the SVG fragment for one blueprint card at (ox, oy)."""
    kind = layout["kind"]
    color = _FAMILY_COLOR.get(kind, _MUTED)
    out = []

    # card frame
    out.append(f'<rect x="{ox}" y="{oy}" width="{CARD_W}" height="{CARD_H}" '
               f'rx="10" fill="{_CANVAS}" stroke="#2a3142" stroke-width="1"/>')

    # header label (id / family)
    label = f'{layout["id"]}'
    fam = f'{kind}/{layout.get("family", "")}'
    out.append(f'<text x="{ox + CARD_PAD}" y="{oy + 18}" font-family="monospace" '
               f'font-size="9" fill="{color}">{_esc(label)}</text>')
    out.append(f'<text x="{ox + CARD_W - CARD_PAD}" y="{oy + 18}" '
               f'text-anchor="end" font-family="monospace" font-size="9" '
               f'fill="{_MUTED}">{_esc(fam)}</text>')

    # inner canvas area for the region map
    ix = ox + INNER_PAD
    iy = oy + 26
    iw = CARD_W - 2 * INNER_PAD
    ih = CARD_H - 26 - INNER_PAD
    out.append(f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" rx="4" '
               f'fill="#12161f" stroke="#222836" stroke-width="0.6"/>')

    regions = layout.get("regions") or {}
    order = layout.get("reading_order") or list(regions.keys())
    rank = {slot: i + 1 for i, slot in enumerate(order)}
    for slot, (x, y, w, h) in regions.items():
        rx = ix + x * iw
        ry = iy + y * ih
        rw = max(2.0, w * iw)
        rh = max(2.0, h * ih)
        out.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" '
                   f'height="{rh:.1f}" rx="3" fill="{color}" fill-opacity="0.14" '
                   f'stroke="{color}" stroke-width="1"/>')
        n = rank.get(slot)
        if n is not None:
            cx = rx + 7
            cy = ry + 7
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" '
                       f'fill="{color}"/>')
            out.append(f'<text x="{cx:.1f}" y="{cy + 3:.1f}" text-anchor="middle" '
                       f'font-family="monospace" font-size="8" fill="#ffffff">'
                       f'{n}</text>')
    return "".join(out)


def _sheet(title: str, layouts: list, subtitle: str = "") -> str:
    """Render a whole contact sheet for the given layouts."""
    n = len(layouts)
    rows = (n + COLS - 1) // COLS
    width = COLS * CARD_W + (COLS + 1) * GAP
    height = HEADER + rows * CARD_H + (rows + 1) * GAP
    parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="{_BG}"/>',
        f'<text x="{GAP}" y="30" font-family="sans-serif" font-size="20" '
        f'font-weight="700" fill="{_INK}">{_esc(title)}</text>',
    ]
    if subtitle:
        parts.append(f'<text x="{width - GAP}" y="30" text-anchor="end" '
                     f'font-family="monospace" font-size="11" fill="{_MUTED}">'
                     f'{_esc(subtitle)}</text>')
    for i, layout in enumerate(layouts):
        r, c = divmod(i, COLS)
        ox = GAP + c * (CARD_W + GAP)
        oy = HEADER + GAP + r * (CARD_H + GAP)
        parts.append(_card(layout, ox, oy))
    parts.append("</svg>")
    return "\n".join(parts)


def _representative(layouts: list, count: int = 25) -> list:
    """Pick a spread across kinds/families for the overview sheet."""
    picked, seen = [], set()
    by_family: dict = {}
    for l in layouts:
        by_family.setdefault((l["kind"], l.get("family", "")), []).append(l)
    # round-robin one per family first, then fill up
    fam_items = list(by_family.values())
    idx = 0
    while len(picked) < count and any(idx < len(v) for v in fam_items):
        for v in fam_items:
            if idx < len(v) and len(picked) < count:
                l = v[idx]
                if l["id"] not in seen:
                    picked.append(l)
                    seen.add(l["id"])
        idx += 1
    return picked[:count]


def emit(out_dir: str) -> dict:
    """Write the four gallery sheets into ``out_dir``; return an info dict."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    all_layouts = _L.all_layouts()

    text_l = _L.by_kind("text")
    image_l = _L.by_kind("image")
    chart_l = _L.by_kind("chart")

    sheets = {
        "overview.svg": ("排版库全览 · 25 套代表",
                         _representative(all_layouts, 25),
                         f"{len(all_layouts)} blueprints"),
        "text.svg": ("文字排版 · 全族", text_l, f"{len(text_l)} blueprints"),
        "image.svg": ("图像排版 · 全族", image_l, f"{len(image_l)} blueprints"),
        "chart.svg": ("图表排版 · 全族", chart_l, f"{len(chart_l)} blueprints"),
    }
    for name, (title, layouts, sub) in sheets.items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_sheet(title, layouts, sub))
        paths[name] = path

    return {"out_dir": out_dir, "layouts": len(all_layouts),
            "text": len(text_l), "image": len(image_l), "chart": len(chart_l),
            "files": paths}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="capability_library.render_gallery",
        description="Render the layout library as SVG contact sheets")
    ap.add_argument("--out", required=True,
                    help="output directory for overview/text/image/chart .svg")
    args = ap.parse_args(argv)
    info = emit(args.out)
    print(f"wrote {len(info['files'])} sheets to {info['out_dir']} "
          f"({info['layouts']} blueprints: text={info['text']} "
          f"image={info['image']} chart={info['chart']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
