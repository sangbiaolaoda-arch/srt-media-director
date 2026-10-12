"""layout_library.py — 100+ composition blueprints for SRT Media Director.

Additive capability library. It does **not** modify the existing composition
pipeline (``composition_planner.py`` / ``skills/06``). It supplies a curated,
machine-validated catalog of *blueprint* region maps — normalized
``(x, y, w, h)`` on the 1280x720 canvas, safe-area aware (``SAFE = 0.07``) —
that the director can draw from when it wants a richer vocabulary than the
built-in 8 templates.

Categories (>=100 layouts in total, deterministic, generated once at import):

    text   — typographic layouts (stacks, hero, columns, pull-quote, stat)
    image  — picture layouts (hero, split, grid, full-bleed, inset, compare)
    chart  — data layouts (donut, bars, line, KPI row, scatter, waterfall)

Every layout is a plain dict::

    {"id", "kind", "name", "family",
     "regions": {slot: (x, y, w, h)},   # normalized canvas fractions
     "alignment_axis", "reading_order": [slot, ...], "capacity": {...}}

Pure data + pure functions; deterministic; no renderer dependency.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Region = Tuple[float, float, float, float]

SAFE = 0.07               # matches runtime/common.py SAFE
CANVAS = (1280, 720)

_LAYOUTS: List[Dict] = []


def _clampf(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _add(**kw) -> None:
    _LAYOUTS.append(kw)


# --------------------------------------------------------------------- text
def _text_stack() -> None:
    """9 layouts: alignment x vertical rhythm."""
    rhythm = {"airy": (0.14, 0.22, 0.44, 0.72),
              "balanced": (0.16, 0.245, 0.46, 0.735),
              "dense": (0.18, 0.27, 0.48, 0.75)}
    align = {"left": (0.07, 0.40), "center": (0.30, 0.40), "right": (0.53, 0.40)}
    for a, (x, w) in align.items():
        for r, (y1, y2, y3, y4) in rhythm.items():
            _add(id=f"text_stack_{a}_{r}", kind="text", family="stack",
                 name=f"文本堆叠·{a}/{r}",
                 regions={"eyebrow": (x, y1, w, 0.050),
                          "title": (x, y2, w, 0.090),
                          "body": (x, y3, w, 0.200),
                          "note": (x, y4, w, 0.060)},
                 alignment_axis=a,
                 reading_order=["eyebrow", "title", "body", "note"],
                 capacity={"max_body_chars": 90 if r == "dense" else 140})


def _text_hero_title() -> None:
    """12 layouts: title position x kicker x rule."""
    for p, ty in (("top", 0.135), ("center", 0.38), ("bottom", 0.64)):
        for kicker in (False, True):
            for rule in (False, True):
                regs: Dict[str, Region] = {"title": (0.10, ty, 0.80, 0.18)}
                order = ["title"]
                if kicker:
                    regs["kicker"] = (0.10, round(ty - 0.065, 3), 0.32, 0.050)
                    order.insert(0, "kicker")
                if rule:
                    regs["rule"] = (0.10, round(ty + 0.195, 3), 0.80, 0.012)
                    order.append("rule")
                regs["byline"] = (0.10, round(ty + 0.235, 3), 0.42, 0.050)
                order.append("byline")
                _add(id=f"text_hero_{p}_{int(kicker)}{int(rule)}", kind="text",
                     family="hero_title", name=f"标题主角·{p}/k{kicker}/r{rule}",
                     regions=regs, alignment_axis="left", reading_order=order,
                     capacity={"max_title_chars": 40})


def _text_two_column() -> None:
    """6 layouts: column ratio x text alignment."""
    for ratio in (0.40, 0.50, 0.60):
        for al in ("left", "justified"):
            lw = round(ratio, 3)
            rx = round(0.07 + lw + 0.06, 3)
            rw = round(0.86 - lw - 0.06, 3)
            _add(id=f"text_twocol_{int(ratio*100)}_{al}", kind="text",
                 family="two_column", name=f"双栏·{int(ratio*100)}/{al}",
                 regions={"left_title": (0.07, 0.14, lw, 0.08),
                          "left_body": (0.07, 0.25, lw, 0.50),
                          "right_title": (rx, 0.14, rw, 0.08),
                          "right_body": (rx, 0.25, rw, 0.50)},
                 alignment_axis=al,
                 reading_order=["left_title", "left_body", "right_title", "right_body"],
                 capacity={"max_body_chars": 110})


def _text_pull_quote() -> None:
    """6 layouts: quote position x attribution style."""
    for p, x, w in (("left", 0.07, 0.55), ("center", 0.20, 0.60), ("right", 0.38, 0.55)):
        for attr in ("below", "inline"):
            regs = {"quote": (x, 0.26, w, 0.30)}
            if attr == "below":
                regs["attribution"] = (x, 0.62, w * 0.6, 0.06)
            else:
                regs["attribution"] = (x, 0.57, w * 0.6, 0.06)
            regs["source"] = (x, 0.71, w * 0.6, 0.05)
            _add(id=f"text_quote_{p}_{attr}", kind="text", family="pull_quote",
                 name=f"引用金句·{p}/{attr}", regions=regs,
                 alignment_axis=p if p != "right" else "right",
                 reading_order=["quote", "attribution", "source"],
                 capacity={"max_quote_chars": 70})


def _text_three_column() -> None:
    """3 layouts: column gap."""
    for gap, tag in ((0.03, "tight"), (0.05, "normal"), (0.08, "wide")):
        cw = (0.86 - 2 * gap) / 3.0
        xs = [0.07, 0.07 + cw + gap, 0.07 + 2 * (cw + gap)]
        widths = [cw, cw, 0.93 - xs[2]]           # last col absorbs rounding
        regs, order = {}, []
        for i, (x, w) in enumerate(zip(xs, widths), 1):
            regs[f"col{i}_title"] = (round(x, 3), 0.14, round(w, 3), 0.07)
            regs[f"col{i}_body"] = (round(x, 3), 0.24, round(w, 3), 0.54)
            order += [f"col{i}_title", f"col{i}_body"]
        _add(id=f"text_threecol_{tag}", kind="text", family="three_column",
             name=f"三栏·{tag}", regions=regs, alignment_axis="left",
             reading_order=order, capacity={"max_body_chars": 70})


def _text_overlay_caption() -> None:
    """3 layouts: eyebrow+title over a reserved media band."""
    for p, my in (("caption_top", 0.07), ("caption_mid", 0.30), ("caption_bottom", 0.60)):
        _add(id=f"text_overlay_{p}", kind="text", family="overlay_caption",
             name=f"文字叠层·{p}",
             regions={"media": (0.07, 0.07, 0.86, 0.52),
                      "eyebrow": (0.11, round(my + 0.02, 3), 0.30, 0.045),
                      "title": (0.11, round(my + 0.075, 3), 0.64, 0.10),
                      "note": (0.11, round(my + 0.19, 3), 0.64, 0.06)},
             alignment_axis="left",
             reading_order=["media", "eyebrow", "title", "note"],
             capacity={"max_title_chars": 36})


def _text_number_stat() -> None:
    """3 layouts: big-number alignment."""
    for a, x, w in (("left", 0.07, 0.45), ("center", 0.25, 0.50), ("right", 0.48, 0.45)):
        _add(id=f"text_stat_{a}", kind="text", family="number_stat",
             name=f"大数字·{a}",
             regions={"number": (x, 0.24, w, 0.26),
                      "label": (x, 0.53, w, 0.06),
                      "note": (x, 0.62, w, 0.09)},
             alignment_axis=a,
             reading_order=["number", "label", "note"],
             capacity={"max_label_chars": 24})


# -------------------------------------------------------------------- image
def _image_hero_caption() -> None:
    """8 layouts: hero scale x caption position."""
    for scale, tag in ((0.86, "full"), (0.60, "safe")):
        hx = round((0.86 - scale) / 2 + 0.07, 3)
        for cap in ("below", "overlay_left", "overlay_bottom", "side"):
            regs = {"hero": (hx, 0.10, scale, 0.62)}
            order = ["hero", "caption"]
            if cap == "below":
                regs["caption"] = (hx, 0.75, scale, 0.10)
            elif cap == "overlay_left":
                regs["caption"] = (round(hx + 0.03, 3), 0.18, 0.34, 0.22)
            elif cap == "overlay_bottom":
                regs["caption"] = (round(hx + 0.03, 3), 0.56, scale - 0.06, 0.12)
            else:  # side
                regs["hero"] = (0.07, 0.15, 0.50, 0.58)
                regs["caption"] = (0.62, 0.28, 0.31, 0.34)
                order = ["hero", "caption"]
            _add(id=f"image_hero_{tag}_{cap}", kind="image", family="hero_caption",
                 name=f"主图配文·{tag}/{cap}", regions=regs,
                 alignment_axis="left", reading_order=order,
                 capacity={"max_caption_chars": 60})


def _image_split() -> None:
    """6 layouts: orientation x ratio."""
    for orient in ("h", "v"):
        for ratio in (0.40, 0.50, 0.60):
            if orient == "h":  # left image / right text
                regs = {"image": (0.07, 0.16, round(0.86 * ratio, 3), 0.56),
                        "text": (round(0.07 + 0.86 * ratio + 0.04, 3), 0.18,
                                 round(0.86 * (1 - ratio) - 0.04, 3), 0.52)}
            else:              # top image / bottom text
                regs = {"image": (0.15, 0.08, 0.70, round(0.72 * ratio, 3)),
                        "text": (0.15, round(0.08 + 0.72 * ratio + 0.03, 3),
                                 0.70, round(0.72 * (1 - ratio) - 0.03, 3))}
            _add(id=f"image_split_{orient}_{int(ratio*100)}", kind="image",
                 family="split", name=f"图文分栏·{orient}/{int(ratio*100)}",
                 regions=regs, alignment_axis="left",
                 reading_order=["image", "text"],
                 capacity={"max_caption_chars": 80})


def _image_grid() -> None:
    """6 layouts: gallery arrangements."""
    cells = {
        "2x2": [(0.07, 0.14, 0.42, 0.32), (0.51, 0.14, 0.42, 0.32),
                (0.07, 0.48, 0.42, 0.32), (0.51, 0.48, 0.42, 0.32)],
        "3x1": [(0.07, 0.30, 0.26, 0.36), (0.37, 0.30, 0.26, 0.36),
                (0.67, 0.30, 0.26, 0.36)],
        "1x3": [(0.07, 0.12, 0.86, 0.20), (0.07, 0.35, 0.86, 0.20),
                (0.07, 0.58, 0.86, 0.20)],
        "2x1": [(0.07, 0.20, 0.42, 0.50), (0.51, 0.20, 0.42, 0.50)],
        "1x2": [(0.15, 0.10, 0.70, 0.34), (0.15, 0.48, 0.70, 0.34)],
        "golden": [(0.07, 0.12, 0.55, 0.70), (0.65, 0.12, 0.28, 0.33),
                   (0.65, 0.49, 0.28, 0.33)],
    }
    for name, regions in cells.items():
        slots = {f"cell{i+1}": r for i, r in enumerate(regions)}
        _add(id=f"image_grid_{name}", kind="image", family="grid",
             name=f"图集·{name}", regions=slots, alignment_axis="left",
             reading_order=list(slots.keys()),
             capacity={"cells": len(regions)})


def _image_fullbleed_text() -> None:
    """4 layouts: full-bleed image with a text safe block."""
    for p, x, y, w, h in (("lower_left", 0.09, 0.60, 0.44, 0.24),
                          ("lower_center", 0.27, 0.62, 0.46, 0.22),
                          ("upper_left", 0.09, 0.12, 0.44, 0.22),
                          ("center", 0.25, 0.38, 0.50, 0.24)):
        _add(id=f"image_fullbleed_{p}", kind="image", family="fullbleed_text",
             name=f"满幅配文·{p}",
             regions={"image": (0.00, 0.00, 1.00, 1.00),
                      "title": (x, y, w, round(h * 0.55, 3)),
                      "note": (x, round(y + h * 0.60, 3), w, round(h * 0.35, 3))},
             alignment_axis="left",
             reading_order=["image", "title", "note"],
             capacity={"max_title_chars": 32})


def _image_portrait_text() -> None:
    """3 layouts: portrait image + caption band."""
    for p, ix, iy, iw, ih in (("left", 0.12, 0.10, 0.34, 0.72),
                              ("center", 0.36, 0.08, 0.28, 0.66),
                              ("right", 0.56, 0.10, 0.34, 0.72)):
        regs = {"portrait": (ix, iy, iw, ih)}
        if p == "center":
            regs["caption"] = (0.20, 0.78, 0.60, 0.10)
        else:
            side_x = 0.56 if p == "left" else 0.12
            regs["caption"] = (round(side_x, 3), 0.26, 0.34, 0.40)
        _add(id=f"image_portrait_{p}", kind="image", family="portrait_text",
             name=f"竖幅配文·{p}", regions=regs, alignment_axis="left",
             reading_order=["portrait", "caption"],
             capacity={"max_caption_chars": 80})


def _image_compare_pair() -> None:
    """4 layouts: side-by-side picture comparison."""
    for split, tag in ((0.50, "half"), (0.58, "wide"), (0.44, "narrow"), (0.34, "side")):
        gap = 0.02
        lw = round(0.86 * split, 3)
        rx = round(0.07 + lw + gap, 3)
        rw = round(0.93 - rx, 3)
        _add(id=f"image_compare_{tag}", kind="image", family="compare_pair",
             name=f"图像对照·{tag}",
             regions={"left_img": (0.07, 0.14, lw, 0.50),
                      "right_img": (rx, 0.14, rw, 0.50),
                      "left_cap": (0.07, 0.66, lw, 0.14),
                      "right_cap": (rx, 0.66, rw, 0.14)},
             alignment_axis="left",
             reading_order=["left_img", "left_cap", "right_img", "right_cap"],
             capacity={"max_caption_chars": 48})


def _image_inset() -> None:
    """3 layouts: main image with an inset detail."""
    for p, ix, iy in (("tl", 0.09, 0.10), ("tr", 0.67, 0.10), ("bl", 0.09, 0.52)):
        _add(id=f"image_inset_{p}", kind="image", family="inset",
             name=f"画中画·{p}",
             regions={"main": (0.12, 0.14, 0.76, 0.60),
                      "inset": (ix, iy, 0.22, 0.26),
                      "note": (0.12, 0.78, 0.76, 0.08)},
             alignment_axis="left",
             reading_order=["main", "inset", "note"],
             capacity={"max_note_chars": 60})


# -------------------------------------------------------------------- chart
def _chart_donut() -> None:
    """9 layouts: donut position x legend placement."""
    for pos, cx in (("center", 0.42), ("left", 0.16), ("right", 0.62)):
        for legend in ("none", "right", "below"):
            regs = {"donut": (cx, 0.18, 0.30, 0.46)}
            order = ["donut"]
            if legend == "right":
                lx = _clampf(cx + 0.32, SAFE, 0.93 - 0.22)
                regs["legend"] = (round(lx, 3), 0.24, 0.22, 0.34)
                order = ["donut", "legend"]
            elif legend == "below":
                lx = _clampf(cx - 0.02, SAFE, 0.93 - 0.34)
                regs["legend"] = (round(lx, 3), 0.66, 0.34, 0.14)
                order = ["donut", "legend"]
            else:
                regs["number"] = (cx, 0.30, 0.30, 0.22)  # hosted centre value
                order = ["donut", "number"]
            _add(id=f"chart_donut_{pos}_{legend}", kind="chart", family="donut",
                 name=f"环形图·{pos}/{legend}", regions=regs,
                 alignment_axis="center", reading_order=order,
                 capacity={"series_max": 6})


def _chart_bars_vertical() -> None:
    """6 layouts: bar block position x title."""
    for pos, x, w in (("center", 0.20, 0.60), ("left", 0.07, 0.55), ("right", 0.38, 0.55)):
        for title in ("top", "none"):
            regs = {"bars": (x, 0.24, w, 0.48)}
            order = ["bars"]
            if title == "top":
                regs["title"] = (x, 0.10, w, 0.08)
                order.insert(0, "title")
            regs["axis_label"] = (x, 0.76, w, 0.06)
            order.append("axis_label")
            _add(id=f"chart_barsv_{pos}_{title}", kind="chart", family="bars",
                 name=f"竖柱图·{pos}/{title}", regions=regs,
                 alignment_axis="center", reading_order=order,
                 capacity={"series_max": 8})


def _chart_bars_horizontal() -> None:
    """6 layouts: horizontal bars position x title."""
    for pos, x, w in (("center", 0.16, 0.68), ("left", 0.07, 0.60), ("right", 0.33, 0.60)):
        for title in ("top", "none"):
            regs = {"bars": (x, 0.20, w, 0.54)}
            order = ["bars"]
            if title == "top":
                regs["title"] = (x, 0.09, w, 0.08)
                order.insert(0, "title")
            regs["axis_label"] = (x, 0.78, w, 0.06)
            order.append("axis_label")
            _add(id=f"chart_barsh_{pos}_{title}", kind="chart", family="bars_h",
                 name=f"横条图·{pos}/{title}", regions=regs,
                 alignment_axis="left", reading_order=order,
                 capacity={"series_max": 8})


def _chart_line() -> None:
    """5 layouts: line chart variants."""
    variants = [
        ("plain", {"line": (0.12, 0.20, 0.76, 0.50)}, ["line"]),
        ("titled", {"title": (0.12, 0.09, 0.76, 0.08), "line": (0.12, 0.20, 0.76, 0.50)},
         ["title", "line"]),
        ("annotated", {"line": (0.12, 0.20, 0.76, 0.46), "annotation": (0.56, 0.10, 0.32, 0.08)},
         ["line", "annotation"]),
        ("dual", {"line_a": (0.12, 0.20, 0.76, 0.44), "line_b": (0.12, 0.20, 0.76, 0.44),
                  "legend": (0.12, 0.70, 0.40, 0.08)}, ["line_a", "line_b", "legend"]),
        ("sparkline_row", {"spark1": (0.10, 0.30, 0.24, 0.14), "spark2": (0.38, 0.30, 0.24, 0.14),
                           "spark3": (0.66, 0.30, 0.24, 0.14)}, ["spark1", "spark2", "spark3"]),
    ]
    for tag, regs, order in variants:
        _add(id=f"chart_line_{tag}", kind="chart", family="line",
             name=f"折线图·{tag}", regions=regs, alignment_axis="left",
             reading_order=order, capacity={"points_max": 24})


def _chart_kpi_row() -> None:
    """3 layouts: KPI card rows."""
    for cols in (2, 3, 4):
        gap = 0.03
        cw = (0.86 - (cols - 1) * gap) / cols
        regs, order = {}, []
        for i in range(cols):
            rx = round(0.07 + i * (cw + gap), 3)
            w = cw if i < cols - 1 else (0.93 - rx)   # last card absorbs rounding
            regs[f"kpi{i+1}"] = (rx, 0.30, round(w, 3), 0.30)
            order.append(f"kpi{i+1}")
        _add(id=f"chart_kpi_{cols}", kind="chart", family="kpi_row",
             name=f"KPI 行·{cols}卡", regions=regs, alignment_axis="left",
             reading_order=order, capacity={"cards": cols})


def _chart_scatter() -> None:
    """3 layouts: scatter placement."""
    for pos, x, w in (("center", 0.18, 0.64), ("left", 0.07, 0.56), ("right", 0.37, 0.56)):
        _add(id=f"chart_scatter_{pos}", kind="chart", family="scatter",
             name=f"散点图·{pos}",
             regions={"scatter": (x, 0.20, w, 0.52),
                      "axis_x": (x, 0.74, w, 0.05),
                      "axis_y": (round(_clampf(x - 0.05, SAFE, 0.93 - 0.05), 3),
                                 0.20, 0.05, 0.52)},
             alignment_axis="left",
             reading_order=["scatter", "axis_x", "axis_y"],
             capacity={"points_max": 40})


def _chart_waterfall() -> None:
    """2 layouts: waterfall orientation."""
    _add(id="chart_waterfall_vertical", kind="chart", family="waterfall",
         name="瀑布图·竖",
         regions={"waterfall": (0.14, 0.22, 0.72, 0.50),
                  "total": (0.70, 0.10, 0.18, 0.08)},
         alignment_axis="center", reading_order=["waterfall", "total"],
         capacity={"steps_max": 6})
    _add(id="chart_waterfall_horizontal", kind="chart", family="waterfall",
         name="瀑布图·横",
         regions={"waterfall": (0.10, 0.20, 0.74, 0.52),
                  "total": (0.60, 0.76, 0.30, 0.08)},
         alignment_axis="left", reading_order=["waterfall", "total"],
         capacity={"steps_max": 6})


def _build() -> None:
    _text_stack()
    _text_hero_title()
    _text_two_column()
    _text_pull_quote()
    _text_three_column()
    _text_overlay_caption()
    _text_number_stat()
    _image_hero_caption()
    _image_split()
    _image_grid()
    _image_fullbleed_text()
    _image_portrait_text()
    _image_compare_pair()
    _image_inset()
    _chart_donut()
    _chart_bars_vertical()
    _chart_bars_horizontal()
    _chart_line()
    _chart_kpi_row()
    _chart_scatter()
    _chart_waterfall()


_build()
_BY_ID = {l["id"]: l for l in _LAYOUTS}


# ------------------------------------------------------------------- API
def all_layouts() -> List[Dict]:
    return list(_LAYOUTS)


def by_kind(kind: str) -> List[Dict]:
    return [l for l in _LAYOUTS if l["kind"] == kind]


def by_family(family: str) -> List[Dict]:
    return [l for l in _LAYOUTS if l["family"] == family]


def ids() -> List[str]:
    return [l["id"] for l in _LAYOUTS]


def get(layout_id: str) -> Dict:
    return _BY_ID[layout_id]


def counts() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for l in _LAYOUTS:
        out[l["kind"]] = out.get(l["kind"], 0) + 1
    out["total"] = len(_LAYOUTS)
    return out


def validate(layout: Dict) -> List[str]:
    """Return a list of contract violations (empty == valid)."""
    errs: List[str] = []
    if not layout.get("id"):
        errs.append("missing id")
    if layout.get("kind") not in ("text", "image", "chart"):
        errs.append(f"bad kind: {layout.get('kind')}")
    regions = layout.get("regions") or {}
    if not regions:
        errs.append("no regions")
    for slot, r in regions.items():
        if len(r) != 4:
            errs.append(f"{slot}: not a 4-tuple")
            continue
        x, y, w, h = r
        if w <= 0 or h <= 0:
            errs.append(f"{slot}: non-positive size")
        if x < -1e-6 or y < -1e-6 or x + w > 1 + 1e-6 or y + h > 1 + 1e-6:
            errs.append(f"{slot}: out of canvas bounds {r}")
        # full-bleed image is an intentional exception to the safe area
        if not (layout["family"] == "fullbleed_text" and slot == "image"):
            if x < SAFE - 1e-6 or y < SAFE - 1e-6 or x + w > 1 - SAFE + 1e-6 or y + h > 1 - SAFE + 1e-6:
                errs.append(f"{slot}: breaches safe area {r}")
    order = layout.get("reading_order")
    if not order:
        errs.append("no reading_order")
    elif set(order) != set(regions.keys()):
        errs.append("reading_order/regions slot mismatch")
    return errs
