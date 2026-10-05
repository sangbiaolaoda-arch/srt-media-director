"""Render a :class:`WorldState` to self-describing HTML for observation.

The layout is derived *deterministically from the world state itself*
(objects ordered by their first-focus time), so the observer is not handed a
hard-coded picture: it must recover ordering, focus and edges from what the
browser actually laid out.

Temporal relations need more than one frame, so the observer replays the whole
timeline: :func:`render_timeline` writes one HTML per keyframe with the *same*
layout but that frame's own focus set. The browser then observes focus moving
over time, which is what ``temporal_precedence`` is checked against.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from world_state.model import WorldState

_W, _H = 180, 80
_X0, _Y0, _DX = 60, 140, 220


def stable_order(ws: WorldState) -> List[str]:
    """Object order by (first-focus time, id) over the whole timeline."""
    first_focus: Dict[str, float] = {}
    for f in ws.frames:
        for oid, o in f.objects.items():
            if o.focus and oid not in first_focus:
                first_focus[oid] = f.t
    all_ids = set()
    for f in ws.frames:
        all_ids.update(f.objects.keys())
    return sorted(all_ids, key=lambda k: (first_focus.get(k, 1e9), k))


def _render_frame(ws: WorldState, frame_index: int, order: List[str],
                  out_path: str, title: str) -> str:
    frame = ws.frames[frame_index]
    parts: List[str] = []
    parts.append("<!doctype html><html><head><meta charset='utf-8'>")
    parts.append("<title>%s@%d</title>" % (title, frame_index))
    parts.append("<style>html,body{margin:0;padding:0;background:#fff;"
                 "font-family:sans-serif}#stage{position:relative;width:680px;height:382px}"
                 ".box{position:absolute;border:2px solid #333;box-sizing:border-box;"
                 "display:flex;align-items:center;justify-content:center}"
                 ".focus{outline:4px solid #d33}.edge{position:absolute;height:2px;"
                 "background:#888;transform-origin:0 0}</style></head><body>"
                 "<div id='stage' data-frame-t='%s'>" % frame.t)

    box_geo: Dict[str, Dict[str, int]] = {}
    for i, oid in enumerate(order):
        obj = frame.objects.get(oid)
        x = _X0 + i * _DX
        y = _Y0
        box_geo[oid] = {"x": x, "y": y}
        visible = bool(obj.visible) if obj else False
        focus = bool(obj.focus) if obj else False
        cls = "box focus" if focus else "box"
        style_vis = "" if visible else "visibility:hidden;"
        parts.append(
            "<div class='%s' data-node='%s' data-focus='%s' "
            "style='%sleft:%dpx;top:%dpx;width:%dpx;height:%dpx'>%s</div>"
            % (cls, oid, "true" if focus else "false", style_vis,
               x, y, _W, _H, oid))

    for r in frame.relations:
        if r.source in box_geo and r.target in box_geo:
            x1 = box_geo[r.source]["x"] + _W
            y1 = box_geo[r.source]["y"] + _H // 2
            x2 = box_geo[r.target]["x"]
            w = max(1, x2 - x1)
            parts.append(
                "<div class='edge' data-rel='1' data-rel-source='%s' "
                "data-rel-target='%s' data-rel-type='%s' data-rel-phase='%s' "
                "style='left:%dpx;top:%dpx;width:%dpx'></div>"
                % (r.source, r.target, r.type, r.phase, x1, y1, w))

    parts.append("</div></body></html>")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    return out_path


def render_world_state(ws: WorldState, out_path: str, title: str = "world") -> str:
    """Render the *final* frame (used for single-frame fidelity checks)."""
    return _render_frame(ws, len(ws.frames) - 1, stable_order(ws), out_path, title)


def render_timeline(ws: WorldState, outdir: str, title: str = "world") -> List[Tuple[str, float]]:
    """Write one HTML per keyframe. Returns ``[(path, t), ...]``."""
    order = stable_order(ws)
    os.makedirs(outdir, exist_ok=True)
    out: List[Tuple[str, float]] = []
    for i, frame in enumerate(ws.frames):
        p = os.path.join(outdir, "frame_%02d.html" % i)
        _render_frame(ws, i, order, p, title)
        out.append((p, frame.t))
    return out


def layout_geometry(order: List[str]) -> Dict[str, Any]:
    """Expose the deterministic layout so tests can assert expected geometry."""
    return {oid: {"x": _X0 + i * _DX, "y": _Y0, "w": _W, "h": _H}
            for i, oid in enumerate(order)}
