"""P2-2 Phase-1 minimal closed loop (real renderer evidence).

Proves:  State -> Delta -> Growth Transition -> Renderer -> t0/t_mid/t1

Entity : revenue_chart
State A: value = 30
State B: value = 70
Transition: growth (positive direction)

The three frames are produced by the REAL raster renderer
(``runtime/raster_renderer.py::draw_frame``) via the new ``growth`` chart kind;
the per-frame value is sampled from the State Delta motion spec
(``runtime/state_delta.py::sample_value``), NOT hard-coded.
"""
import json
import os
import sys
import hashlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "runtime"))
sys.path.insert(0, HERE)

import state_delta as sd                      # noqa: E402
from PIL import Image                          # noqa: E402
import raster_renderer as rr                   # noqa: E402

W, H = rr.W, rr.H
OUT = os.path.join(HERE, "docs", "p2-2-phase1-evidence")
os.makedirs(OUT, exist_ok=True)

IDENT = "revenue_chart"
VAL_A, VAL_B = 30.0, 70.0
VMAX = 75.0
SPAN = (0.0, 2.0)          # absolute seconds of the beat
T0, T_MID, T1 = 0.0, 1.0, 2.0


def make_states():
    a = {"id": "b1_chart", "identity": IDENT, "type": "chart", "role": "primary",
         "state": {"value": VAL_A, "status": "normal"}}
    b = {"id": "b2_chart", "identity": IDENT, "type": "chart", "role": "primary",
         "state": {"value": VAL_B, "status": "normal"}}
    return a, b


def analyze(img, positive_rgb):
    """Return (bar_height_px, changed_ink_px) measured from real pixels."""
    px = img.convert("RGB").load()
    cx = int(W * 0.5)
    base_y = int(H * 0.90)
    top = None
    for y in range(int(H * 0.05), base_y):
        r, g, b = px[cx, y]
        if abs(r - positive_rgb[0]) + abs(g - positive_rgb[1]) + abs(b - positive_rgb[2]) < 30:
            top = y
            break
    height = 0 if top is None else base_y - top
    return height


def main():
    a, b = make_states()

    # 1) identity matching (explicit field only)
    matches = sd.match_identity([a], [b])

    # 2) state -> delta
    sa = sd.entity_state(a)
    sb = sd.entity_state(b)
    deltas = sd.derive_delta(sa, sb, reason="revenue grew from 30 to 70")
    dd = [sd.as_dict(d) for d in deltas]

    # 3) delta -> transition
    trans = sd.classify_transition("b1", "b2", [m.entity_id for m in matches], deltas)

    # 4) transition -> motion grammar
    vdelta = [d for d in deltas if d.kind == "value"][0]
    spec = sd.compile_motion(vdelta, SPAN)

    # 5) executor: sample value at t0 / t_mid / t1
    v_t0 = sd.sample_value(spec, T0)
    v_tmid = sd.sample_value(spec, T_MID)
    v_t1 = sd.sample_value(spec, T1)

    # 6) render through the REAL renderer
    positive = rr.hex2rgb(rr.COLORS["positive"])
    frames = {}
    heights = {}
    for tag, t, val in (("t0", T0, v_t0), ("t_mid", T_MID, v_tmid), ("t1", T1, v_t1)):
        beat = {
            "beat_id": "b1", "start_sec": 0.0, "end_sec": 2.0,
            "strategy": "growth", "camera": {},
            "elements": [{"id": "b1_chart", "identity": IDENT, "type": "chart",
                          "role": "primary", "color_role": "positive",
                          "chart": {"kind": "growth", "value": round(val, 4), "vmax": VMAX}}],
        }
        plan = {"beat_id": "b1", "boxes": {"b1_chart": {"x": W * 0.30, "y": H * 0.20,
                                                         "w": W * 0.40, "h": H * 0.62}},
                "fonts": {"b1_chart": {"size": 22, "bold": True}}}
        ent = {"beat_id": "b1",
               "lifecycle": {"b1_chart": {"enter": {"motion": "inherit", "at": 0.0, "dur": 0.0}}},
               "events": []}
        img = rr.draw_frame(beat, plan, ent, t)
        path = os.path.join(OUT, "frame_%s.png" % tag)
        img.save(path)
        frames[tag] = path
        heights[tag] = analyze(img, positive)

    frame_sha = {}
    for tag, path in frames.items():
        with open(path, "rb") as fh:
            frame_sha[tag] = hashlib.sha256(fh.read()).hexdigest()

    # 7) validation rules
    issues = sd.validate_deltas(deltas, span=SPAN)

    evidence = {
        "entity": IDENT,
        "state_a": {"value": VAL_A},
        "state_b": {"value": VAL_B},
        "identity_matches": [sd.as_dict(m) for m in matches],
        "delta": dd,
        "delta_reason": dd[0]["reason"] if dd else None,
        "delta_direction": [d.direction() for d in deltas],
        "transition": sd.as_dict(trans),
        "motion": {"action": spec.action, "span": list(SPAN)},
        "sampled_value": {"t0": round(v_t0, 4), "t_mid": round(v_tmid, 4), "t1": round(v_t1, 4)},
        "rendered_bar_height_px": heights,
        "frame_sha256": frame_sha,
        "frames": frames,
        "validate_issues": issues,
    }
    with open(os.path.join(OUT, "evidence.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)

    # ---- acceptance checks ----
    checks = {
        "identity_present": bool(matches) and matches[0].entity_id == IDENT,
        "delta_has_reason": bool(dd) and bool(dd[0]["reason"]),
        "growth_direction_positive": spec.action == "growth" and vdelta.direction() == "up",
        "t0_equals_A": abs(v_t0 - VAL_A) < 1e-6,
        "t1_equals_B": abs(v_t1 - VAL_B) < 1e-6,
        "t_mid_strictly_between": VAL_A < v_tmid < VAL_B,
        "real_interpolation_not_jump": heights["t0"] < heights["t_mid"] < heights["t1"],
        "fade_alone_cannot_pass": heights["t_mid"] > heights["t0"],  # height grows, not just alpha
        "no_validate_issues": issues == [],
    }
    print(json.dumps({"checks": checks, "evidence": evidence}, indent=2, ensure_ascii=False))
    if not all(checks.values()):
        sys.exit(1)
    print("\nPHASE-1 CLOSED LOOP: PASS")


if __name__ == "__main__":
    main()
