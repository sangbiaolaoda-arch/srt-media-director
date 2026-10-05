"""Stage 4 — Composition planner: semantic layout → pixel boxes.

Responsibilities (skill: 06-composition):
- assign every element to a region from a strategy template (Composition Blueprint);
- measure *real* text footprints (Content Footprint Preflight) before solving;
- solve all layers (subject / text / annotation) in ONE pass, not independently;
- run the R-gates plus pragmatic A-gates, and REFUSE to emit a render plan when
  a hard gate fails (LayoutIntentIncomplete instead of guessing coordinates).

Coordinates are pixels on the 1280×720 canvas. Regions in templates are
normalized (x, y, w, h) hints — the Blueprint — and text boxes are then
re-centered on the *measured* footprint inside their region.
"""
import math

from common import CANVAS_W as W, CANVAS_H as H, SAFE, measure_text
from geometry import legacy as _geom_legacy

FONT_SIZES = {
    "eyebrow": 20, "note": 22, "label": 26, "keyword": 44,
    "display_small": 40, "display": 52, "word": 56, "number": 96,
}

# Composition Blueprint templates: normalized (x, y, w, h) regions per slot.
TEMPLATES = {
    "_text_top": {
        "eyebrow": (0.070, 0.075, 0.34, 0.055),
        "title": (0.070, 0.125, 0.62, 0.095),
    },
    "single_focus": {
        "hero": (0.355, 0.235, 0.29, 0.42),
        "keyword": (0.290, 0.690, 0.42, 0.105),
        "note": (0.290, 0.820, 0.42, 0.075),
    },
    "left_to_right_flow": {
        "hero_left": (0.090, 0.330, 0.230, 0.340),
        "bridge": (0.405, 0.430, 0.190, 0.130),
        "hero_right": (0.680, 0.330, 0.230, 0.340),
        "note": (0.320, 0.760, 0.360, 0.080),
    },
    "cause_effect": {
        "cause": (0.085, 0.380, 0.270, 0.190),
        "bridge": (0.405, 0.430, 0.190, 0.130),
        "result": (0.675, 0.380, 0.270, 0.190),
        "note": (0.320, 0.700, 0.360, 0.080),
    },
    "comparison": {
        "panel_left": (0.070, 0.240, 0.400, 0.520),
        "panel_right": (0.530, 0.240, 0.400, 0.520),
        "word_left": (0.120, 0.330, 0.300, 0.150),
        "word_right": (0.580, 0.330, 0.300, 0.150),
        "note_left": (0.120, 0.530, 0.300, 0.120),
        "note_right": (0.580, 0.530, 0.300, 0.120),
    },
    "center_cluster": {
        "hero": (0.370, 0.225, 0.260, 0.410),
        "number": (0.370, 0.225, 0.260, 0.410),  # hosted inside the donut
        "note": (0.280, 0.700, 0.440, 0.085),
    },
    "before_after": {
        "hero": (0.240, 0.280, 0.520, 0.400),
        "delta": (0.430, 0.190, 0.140, 0.085),
        "note": (0.280, 0.740, 0.440, 0.085),
    },
}

# P0① 构图弱约束：6 个模板不再是「必须套用」的固定长相，而是**建议锚点**。
# 元素可自带归一化 rect（自由落位）绕开模板；未知 slot 且无自带区域时才触发
# LAYOUT_INTENT_INCOMPLETE，以继续保证「坐标必须有意为之、不许猜」。
# 模板角色从「定义画面」降为「兜底参考」——固定审美原则，不固定长相。
COMPOSITION_POLICY = {
    "templates_are": "advisory",   # advisory（建议）而非 mandatory（强制）
    "free_placement": True,        # 允许元素自带归一化 rect
    "unknown_slot": "reject",      # 仍拒绝无意图坐标
}


def _rect(norm):
    # delegate to the canonical box vocabulary (behavior-preserving)
    return _geom_legacy.planner_rect(norm, W, H)


def _intersect(a, b):
    return _geom_legacy.planner_intersect(a, b)


def _area(b):
    return _geom_legacy.planner_area(b)


def _center_of(b):
    return _geom_legacy.planner_center(b)


def _proximity_pairs(beat, boxes):
    """接近性（Gestalt proximity）：bound_to 关系对必须明显靠近——
    有关系才靠近，没关系才分开；这是「不松散」的机器化表达。"""
    out = []
    diag = (W ** 2 + H ** 2) ** 0.5
    for rel in beat.get("relations", []):
        if rel["type"] != "bound_to":
            continue
        a, b = boxes.get(rel["from"]), boxes.get(rel["to"])
        if not a or not b:
            continue
        d = math.hypot(_center_of(a)[0] - _center_of(b)[0],
                       _center_of(a)[1] - _center_of(b)[1]) / diag
        out.append({"from": rel["from"], "to": rel["to"],
                    "distance_ratio": round(d, 3), "ok": d <= 0.28})
    return out


def _visual_balance(beat, boxes):
    """左右视觉重量（仅主体级 primary/secondary；题头与装饰氛围层不计）。"""
    wl = wr = 0.0
    for e in beat["elements"]:
        if e["role"] not in ("primary", "secondary"):
            continue
        b = boxes[e["id"]]
        wgt = _area(b) * (3.0 if e["role"] == "primary" else 2.0)
        cx = _center_of(b)[0]
        if cx < W * 0.48:
            wl += wgt
        elif cx > W * 0.52:
            wr += wgt
        else:
            wl += wgt / 2.0
            wr += wgt / 2.0
    ratio = min(wl, wr) / max(wl, wr) if max(wl, wr) > 0 else 1.0
    return {"left": round(wl, 1), "right": round(wr, 1),
            "balance_ratio": round(ratio, 3), "ok": ratio >= 0.30}


class LayoutIntentIncomplete(Exception):
    pass


def plan_beat(beat):
    """Solve one beat → (boxes, fonts, footprint, intent, audit)."""
    strategy = beat["strategy"]
    tpl = dict(TEMPLATES.get("_text_top", {}))
    tpl.update(TEMPLATES.get(strategy, {}))
    boxes, fonts, footprint = {}, {}, {}

    for el in beat["elements"]:
        if el["type"] == "decor":  # 装饰附体：自带归一化 rect，不参与模板区域预算
            box = _rect(el["rect"])
            boxes[el["id"]] = box
            if el.get("text"):  # 幽灵大字：按区域高度取特大号字
                fonts[el["id"]] = {"size": max(60, int(box["h"] * 0.52)),
                                   "bold": True}
                footprint[el["id"]] = {"mode": "measured", "w": round(box["w"], 1),
                                       "h": round(box["h"], 1)}
            else:
                footprint[el["id"]] = {"mode": "region", "w": round(box["w"], 1),
                                       "h": round(box["h"], 1)}
            continue
        slot = el["slot"]
        if el.get("rect") is not None:      # P0① 自由落位：元素自带区域，模板仅作建议
            box = _rect(el["rect"])
        elif slot in tpl:
            box = _rect(tpl[slot])
        else:
            raise LayoutIntentIncomplete(
                "LAYOUT_INTENT_INCOMPLETE: slot '%s' has no region in strategy '%s'"
                % (slot, strategy))
        if el["type"] == "text":
            size = FONT_SIZES[el.get("size", "label")]
            tw, th = measure_text(el["text"], size, bold=bool(el.get("emphasis")))
            pad = 18 if el.get("boxed") else 6
            tw, th = tw + pad * 2, th + pad * 2
            if tw > box["w"] or th > box["h"] * 1.6:
                raise LayoutIntentIncomplete(
                    "LAYOUT_INTENT_INCOMPLETE: text '%s' (%dx%d) does not fit region %s"
                    % (el["text"], tw, th, slot))
            box = {"x": box["x"] + (box["w"] - tw) / 2,
                   "y": box["y"] + (box["h"] - th) / 2, "w": tw, "h": th}
            fonts[el["id"]] = {"size": size, "bold": bool(el.get("emphasis"))}
            footprint[el["id"]] = {"mode": "measured", "w": round(tw, 1), "h": round(th, 1)}
        elif el["type"] == "chart":
            side = min(box["w"], box["h"])
            box = {"x": box["x"] + (box["w"] - side) / 2,
                   "y": box["y"] + (box["h"] - side) / 2, "w": side, "h": side}
            footprint[el["id"]] = {"mode": "geometry", "w": round(side, 1), "h": round(side, 1)}
        else:
            footprint[el["id"]] = {"mode": "region", "w": round(box["w"], 1),
                                   "h": round(box["h"], 1)}
        boxes[el["id"]] = box

    audit = audit_boxes(beat, boxes)
    roles = {e["id"]: e["role"] for e in beat["elements"]}
    used = sum(_area(b) for eid, b in boxes.items() if roles[eid] != "ambient")
    intent = {
        "strategy": strategy,
        "reading_order": [e["id"] for e in sorted(
            beat["elements"], key=lambda e: {"primary": 0, "secondary": 1}.get(e["role"], 2))],
        "alignment_axes": ["title/eyebrow share left axis x=0.07",
                           "hero group centered on canvas midline x=0.50"],
        "occlusion_policy": "semantic_only (hosted text inside its chart is intentional)",
        "whitespace_budget": round(1.0 - used / float(W * H), 3),
        "proximity_pairs": _proximity_pairs(beat, boxes),
        "visual_balance": _visual_balance(beat, boxes),
    }
    return boxes, fonts, footprint, intent, audit


def audit_boxes(beat, boxes):
    """Hard gates (R-class) + pragmatic aesthetic checks (A-class subset).

    R1 single visual center · R2 text not on figures · R3 annotation overlap ·
    R5 safe area · A15 focus breathing · A19 scale hierarchy (typed compare).
    """
    issues = []
    els = {e["id"]: e for e in beat["elements"]}

    def add(code, msg):
        issues.append({"code": code, "msg": msg})

    primaries = [e for e in beat["elements"] if e["role"] == "primary"]
    if len(primaries) != 1:
        add("R1_SINGLE_FOCUS", "primary count = %d (expected 1)" % len(primaries))

    for eid, b in boxes.items():
        if els[eid]["role"] == "ambient":
            continue
        if b["x"] < W * SAFE - 2 or b["y"] < H * SAFE - 2 \
                or b["x"] + b["w"] > W * (1 - SAFE) + 2 \
                or b["y"] + b["h"] > H * (1 - SAFE) + 2:
            add("R5_SAFE_AREA", "%s outside safe area" % eid)

    hosted = {(e["id"], e["host"]) for e in beat["elements"] if e.get("host")}
    text_ids = [e["id"] for e in beat["elements"] if e["type"] == "text"]
    fig_ids = [e["id"] for e in beat["elements"] if e["type"] in ("motif", "chart")]
    for t in text_ids:
        for f in fig_ids:
            if (t, f) in hosted:
                continue
            if _intersect(boxes[t], boxes[f]):
                add("R2_TEXT_ON_FIGURE", "%s overlaps %s" % (t, f))
    for i in range(len(text_ids)):
        for j in range(i + 1, len(text_ids)):
            a, b = text_ids[i], text_ids[j]
            if a.rsplit("_", 1)[0] != b.rsplit("_", 1)[0]:
                continue
            sa, sb = els[a]["slot"], els[b]["slot"]
            same_zone = (sa.endswith("_left") and sb.endswith("_left")) or \
                        (sa.endswith("_right") and sb.endswith("_right")) or \
                        (sa in ("note", "keyword", "number")
                         and sb in ("note", "keyword", "number"))
            if same_zone and _intersect(boxes[a], boxes[b]):
                add("R3_ANNOTATION_OVERLAP", "%s overlaps %s" % (a, b))

    # A19 scale hierarchy — typed comparison:
    # · primary text: no other text may use a larger font size;
    # · primary figure/chart: must not be smaller than secondary figures
    #   (its declared host is exempt — a chart hosting a number is one unit).
    if primaries:
        p = primaries[0]
        if p["type"] == "text":
            psize = FONT_SIZES.get(p.get("size", "label"), 26)
            for e in beat["elements"]:
                if e["type"] == "text" and e["id"] != p["id"]:
                    if FONT_SIZES.get(e.get("size", "label"), 26) > psize:
                        add("A19_SCALE_HIERARCHY",
                            "text %s larger than primary text %s" % (e["id"], p["id"]))
        else:
            pw = _area(boxes[p["id"]])
            for e in beat["elements"]:
                if e["role"] == "secondary" and e["type"] != "text" \
                        and e["id"] != p.get("host"):
                    if pw < _area(boxes[e["id"]]) * 0.8:
                        add("A19_SCALE_HIERARCHY",
                            "primary %s weaker than secondary %s" % (p["id"], e["id"]))

    # A20 proximity: bound_to pairs must sit close (relations imply nearness).
    for pair in _proximity_pairs(beat, boxes):
        if not pair["ok"]:
            add("A20_PROXIMITY", "%s ~ %s too far (%.2f diag)"
                % (pair["from"], pair["to"], pair["distance_ratio"]))

    # A21 visual balance: subject-level weight must not be lopsided.
    vb = _visual_balance(beat, boxes)
    if not vb["ok"]:
        add("A21_VISUAL_BALANCE",
            "left/right subject weight unbalanced (%.2f)" % vb["balance_ratio"])

    # A15 focus breathing ring around the primary (top-band text exempt).
    if primaries:
        pb = boxes[primaries[0]["id"]]
        ring = {"x": pb["x"] - 16, "y": pb["y"] - 16,
                "w": pb["w"] + 32, "h": pb["h"] + 32}
        for e in beat["elements"]:
            if e["id"] == primaries[0]["id"] or e["role"] == "ambient":
                continue
            if e.get("host") == primaries[0]["id"] or primaries[0].get("host") == e["id"]:
                continue
            if e["slot"] in ("eyebrow", "title"):
                continue
            if _intersect(ring, boxes[e["id"]]):
                add("A15_FOCUS_BREATHING",
                    "%s intrudes the primary breathing ring" % e["id"])

    hard = [i for i in issues if i["code"].startswith("R") or i["code"].startswith("A19")]
    return {"status": "PASS" if not hard else "FAIL", "issues": issues}


def plan(dsl):
    """Solve every beat once. Raises LayoutIntentIncomplete on hard failure."""
    render_beats, intents, footprints, audits = [], {}, {}, {}
    for beat in dsl["beats"]:
        boxes, fonts, footprint, intent, audit = plan_beat(beat)
        if audit["status"] != "PASS":
            raise LayoutIntentIncomplete(
                "composition audit failed for %s: %s" % (beat["beat_id"], audit["issues"]))
        render_beats.append({
            "beat_id": beat["beat_id"], "start_sec": beat["start_sec"],
            "end_sec": beat["end_sec"], "strategy": beat["strategy"],
            "boxes": boxes, "fonts": fonts,
        })
        intents[beat["beat_id"]] = intent
        footprints[beat["beat_id"]] = footprint
        audits[beat["beat_id"]] = audit
    return ({"canvas": dsl["canvas"], "beats": render_beats},
            {"beats": intents}, footprints,
            {"status": "PASS", "beats": audits})
