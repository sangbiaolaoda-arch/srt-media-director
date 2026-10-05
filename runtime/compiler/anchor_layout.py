"""Spec §15/§16 — Semantic layout: anchor / relation / distance → pixels.

The agent expresses intent (anchor, relation, distance, alignment, region);
this module is the Constraint→Pixel step that resolves it to x/y/w/h. Raw
absolute coordinates are deliberately *not* an input here — the whole point is
that the layout system owns the pixels.
"""
from __future__ import annotations

ANCHORS = ("center", "top", "bottom", "left", "right", "top_left", "top_right",
           "bottom_left", "bottom_right", "center_left", "center_right",
           "left_third", "center_third", "right_third", "upper_third", "lower_third")

RELATIONS = ("left_of", "right_of", "above", "below", "inside", "outside",
             "surround", "between", "aligned_with", "attached_to")

DISTANCE = {"near": 0.06, "medium": 0.14, "far": 0.26}

_ANCHOR_XY = {
    "center": (0.5, 0.5), "top": (0.5, 0.0), "bottom": (0.5, 1.0),
    "left": (0.0, 0.5), "right": (1.0, 0.5),
    "top_left": (0.0, 0.0), "top_right": (1.0, 0.0),
    "bottom_left": (0.0, 1.0), "bottom_right": (1.0, 1.0),
    "center_left": (0.0, 0.5), "center_right": (1.0, 0.5),
    "left_third": (1.0 / 6, 0.5), "center_third": (0.5, 0.5), "right_third": (5.0 / 6, 0.5),
    "upper_third": (0.5, 1.0 / 6), "lower_third": (0.5, 5.0 / 6),
}


def anchor_xy(anchor, W, H):
    ax, ay = _ANCHOR_XY.get(anchor, (0.5, 0.5))
    return ax * W, ay * H


def _clamp_box(x, y, w, h, W, H):
    x = max(0.0, min(x, max(0.0, W - w)))
    y = max(0.0, min(y, max(0.0, H - h)))
    return [round(x, 2), round(y, 2), round(w, 2), round(h, 2)]


def _anchor_box(anchor, W, H, w, h):
    cx, cy = anchor_xy(anchor, W, H)
    return _clamp_box(cx - w / 2.0, cy - h / 2.0, w, h, W, H)


def _related_box(rel, ref_box, W, H, w, h, distance):
    rx, ry, rw, rh = ref_box
    rcx, rcy = rx + rw / 2.0, ry + rh / 2.0
    d = DISTANCE.get(distance, DISTANCE["medium"]) * min(W, H)
    if rel == "left_of":
        x, y = rcx - rw / 2.0 - d - w, rcy - h / 2.0
    elif rel == "right_of":
        x, y = rcx + rw / 2.0 + d, rcy - h / 2.0
    elif rel == "above":
        x, y = rcx - w / 2.0, rcy - rh / 2.0 - d - h
    elif rel == "below":
        x, y = rcx - w / 2.0, rcy + rh / 2.0 + d
    elif rel == "inside":
        x, y = rx + (rw - w) / 2.0, ry + (rh - h) / 2.0
    elif rel == "outside":
        x, y = rcx + rw / 2.0 + d, rcy - h / 2.0
    else:  # aligned_with / attached_to / surround / between fall back to offset
        x, y = rcx - w / 2.0, ry - d - h
    return _clamp_box(x, y, w, h, W, H)


def solve(spec, W, H):
    """spec: {'elements':[{'id','anchor'?,'relation'?,'relative_to'?,'distance'?,'size':(w,h)}]}

    Two passes: anchor-only elements resolve first, then related elements use
    their resolved partner's box. Return {'boxes', 'unresolved'}.
    """
    pending = list(spec.get("elements", []))
    boxes = {}
    guard = 0
    while pending and guard < 100:
        guard += 1
        remaining = []
        for e in pending:
            eid = e.get("id")
            if eid in boxes:
                continue
            w, h = e.get("size", (W * 0.2, H * 0.1))
            rel = e.get("relation")
            ref = e.get("relative_to")
            if rel and ref:
                if ref in boxes:
                    boxes[eid] = _related_box(rel, boxes[ref], W, H, w, h,
                                              e.get("distance", "medium"))
                else:
                    remaining.append(e)
            else:
                boxes[eid] = _anchor_box(e.get("anchor", "center"), W, H, w, h)
        if len(remaining) == len(pending):
            return {"boxes": boxes, "unresolved": [e["id"] for e in remaining]}
        pending = remaining
    return {"boxes": boxes, "unresolved": []}


def rejects_raw_coordinates(spec):
    """Spec §15: absolute x/y on an element is a smell (should be semantic)."""
    bad = []
    for e in spec.get("elements", []):
        if "x" in e or "y" in e:
            bad.append(e.get("id"))
    return bad
