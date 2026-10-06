"""spec_test.py — independent gate suite for the 42-rule behavior spec (v7.5).

Runs alongside `self_test.py` (which must stay green) but is a SEPARATE entry
point so it never perturbs the existing pipeline gates. Each check drives one
spec module with a synthetic fixture and asserts the module both PASSES good
input and FAILS the targeted violation — evidence the gate actually bites.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime")
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_PASS, _FAIL = [], []


def check(name, cond):  # noqa: A001
    (_PASS if cond else _FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name)
    return cond


def _good_beat():
    return {
        "beat_id": "b_good", "start_sec": 0, "end_sec": 3.0, "strategy": "top_down",
        "semantic_shape": "Hierarchy", "scene_id": "s1",
        "elements": [
            {"id": "e_title", "type": "text", "role": "primary", "size": "title",
             "text": "核心命题", "color_role": "ink", "visible": True,
             "box": [0.10, 0.12, 0.34, 0.20]},
            {"id": "e_note", "type": "text", "role": "support", "size": "note",
             "text": "说明", "color_role": "muted", "visible": True,
             "box": [0.10, 0.40, 0.22, 0.08]},
        ],
        "boxes": {"e_title": [0.10, 0.12, 0.34, 0.20], "e_note": [0.10, 0.40, 0.22, 0.08]},
        "relations": [{"from": "e_note", "to": "e_title", "type": "below"}],
        "canvas_w": 1.0, "canvas_h": 1.0,
        "style": {"font": "sans", "stroke": 1.25, "radius": 12,
                  "line_weight": 1.5, "icon_style": "line", "chart_style": "bar",
                  "motion_style": "rise"},
    }


def _good_plan():
    b1 = _good_beat()
    b2 = _good_beat()
    b2 = dict(b2, beat_id="b_good2", start_sec=3.0, end_sec=6.0,
              scene_id="s1",
              elements=[dict(e) for e in b1["elements"]],
              continuity=[{"entity": "e_title", "action": "PERSIST"},
                          {"entity": "e_note", "action": "HIDE"}])
    return {"beats": [b1, b2]}


# ------------------------------------------------------------------ checks
def t_hierarchy():
    from director.hierarchy import audit_hierarchy, visual_weight
    good = audit_hierarchy(_good_beat())
    bad_beat = _good_beat()
    bad_beat["elements"].append(
        {"id": "e_decor", "type": "motif", "role": "decor", "visible": True,
         "box": [0.0, 0.0, 1.0, 1.0]})              # huge decoration
    bad_beat["boxes"]["e_decor"] = [0.0, 0.0, 1.0, 1.0]
    bad = audit_hierarchy(bad_beat)
    check("R05/R06 hierarchy: good PASS", good["status"] == "PASS")
    check("R05/R06 hierarchy: decoration overreach FAILs",
          bad["status"] == "FAIL" and any(i["code"] == "DECORATION_OVERREACH"
                                          for i in bad["issues"]))
    check("R05 weight is a number", isinstance(visual_weight(_good_beat()["elements"][0]), float))


def t_continuity():
    from director.continuity_graph import audit_continuity, persist_ratio, build_continuity_graph
    good = audit_continuity(_good_plan()["beats"])
    reset = [{"beat_id": "a", "elements": [{"id": "x"}]},
             {"beat_id": "b", "elements": [{"id": "y"}]}]
    bad = audit_continuity(reset)
    check("R07 continuity: good PASS", good["status"] == "PASS")
    check("R07 continuity: full reset WARNs",
          any(i["code"] == "CONTINUITY_RESET" for i in bad["issues"]))
    check("R08 persist_ratio in [0,1]", 0.0 <= persist_ratio(_good_plan()["beats"]) <= 1.0)
    check("R07 graph has nodes/edges", "nodes" in build_continuity_graph(_good_plan()["beats"]))


def t_anchor():
    from compiler.anchor_layout import solve, rejects_raw_coordinates
    spec = {"elements": [
        {"id": "a", "anchor": "center", "size": (200, 100)},
        {"id": "b", "relation": "right_of", "relative_to": "a", "distance": "near",
         "size": (120, 80)},
    ]}
    r = solve(spec, 1280, 720)
    check("R15 anchor: all resolved", r["unresolved"] == [] and set(r["boxes"]) == {"a", "b"})
    check("R16 relation: b sits right of a",
          r["boxes"]["b"][0] > r["boxes"]["a"][0] + r["boxes"]["a"][2] - 1)
    check("R03 raw coords rejected", rejects_raw_coordinates(
        {"elements": [{"id": "z", "x": 5, "y": 6}]}) == ["z"])


def t_negative_space():
    from compiler.negative_space import audit_negative_space, density
    good = audit_negative_space(_good_beat())
    packed = _good_beat()
    packed["elements"] = [{"id": "p%d" % i, "role": "support"}
                          for i in range(6)]
    packed["boxes"] = {"p%d" % i: [0.0, 0.0, 0.6, 0.6] for i in range(6)}
    bad = audit_negative_space(packed)
    check("R17 negative space: good PASS", good["status"] == "PASS")
    check("R17 density: packed FAILs",
          bad["status"] == "FAIL" and any(i["code"] == "DENSITY_TOO_HIGH" for i in bad["issues"]))
    check("R17 density is numeric", isinstance(density(_good_beat()["boxes"]), float))


def t_budget():
    from compiler.visual_budget import audit_budget, tier_for, budget_for
    check("R19 tier grows with duration",
          [tier_for(d) for d in (1.0, 2.0, 4.0, 7.0)] == ["low", "medium", "rich", "evolving"])
    good = audit_budget(_good_beat())
    heavy = _good_beat()
    heavy["elements"] = [{"id": "t%d" % i, "type": "text", "role": "support",
                          "text": "很长的一段说明文字内容", "visible": True,
                          "motion_policy": {"type": "fade"}} for i in range(6)]
    heavy["boxes"] = {e["id"]: [0, 0, 0.1, 0.1] for e in heavy["elements"]}
    bad = audit_budget(heavy, strict=True)
    check("R18 budget: good PASS", good["status"] == "PASS")
    check("R18 budget: overload FAILs (strict)",
          bad["status"] == "FAIL" and any(i["code"].startswith("BUDGET") for i in bad["issues"]))
    check("R18 budget ceilings present", budget_for(2.0)["max_elements"] >= 1)


def t_family():
    from compiler.composition_family import (FAMILIES, choose_family, strategies,
                                             validate_families, audit_beats)
    check("R36 family: 16 families defined", len(FAMILIES) == 16)
    check("R37 family: every family has >=1 strategy",
          validate_families()["status"] == "PASS")
    check("R36 choose_family resolves alias", choose_family("grow") == "Growth")
    check("R36 strategies non-empty", len(strategies("Comparison")) >= 1)
    bad = audit_beats([{"beat_id": "x", "semantic_shape": "zzz"}])
    check("R36 unknown shape flagged",
          any(i["code"] == "FAMILY_UNKNOWN" for i in bad["issues"]))


def t_style_lock():
    from compiler.style_lock import audit_plan, reuse_decision
    good = audit_plan(_good_plan())
    broken = _good_plan()
    broken["beats"][1]["style"] = dict(broken["beats"][1]["style"], radius=99)
    bad = audit_plan(broken)
    check("R38 style lock: good PASS", good["status"] == "PASS")
    check("R38 style lock: scene mismatch flagged",
          any(i["code"] == "STYLE_LOCK_VIOLATION" for i in bad["issues"]))
    check("R39 reuse-first order", reuse_decision(
        {"motif": True, "style": True}, {"motif": True}) == "motif")


def t_anti_ppt():
    from validation.anti_ppt import audit
    good = audit(_good_plan())
    ppt = {"beats": [{
        "beat_id": "p", "visible": True,
        "elements": ([{"id": "t", "type": "text", "size": "title", "visible": True}]
                     + [{"id": "i", "type": "shape", "visible": True}]
                     + [{"id": "b%d" % i, "type": "text", "size": "bullet",
                         "visible": True} for i in range(3)]),
        "boxes": {"b0": [0.1, 0.7, 0.2, 0.05], "b1": [0.1, 0.75, 0.2, 0.05],
                  "b2": [0.1, 0.8, 0.2, 0.05], "t": [0.1, 0.72, 0.2, 0.05]},
        "visual_balance": {"even": True},
    }]}
    bad = audit(ppt)
    check("R28 anti-ppt: good has no err", good["status"] == "PASS")
    check("R28 anti-ppt: title+icon+bullets WARNs",
          "PPT_TITLE_ICON_BULLETS" in bad["codes"])
    check("R34 anti-ppt: strict escalates to FAIL", audit(ppt, strict=True)["status"] == "FAIL")


def t_cognitive():
    from validation.cognitive_load import audit, load_index
    good = audit(_good_plan())
    heavy = {"beats": [{"beat_id": "c", "start_sec": 0, "end_sec": 1.0,
                        "elements": [{"id": "t%d" % i, "type": "text",
                                      "text": "这是一段很长很长的文字内容需要阅读",
                                      "visible": True} for i in range(6)]}]}
    bad = audit(heavy)
    check("R29 cognitive: good PASS", good["status"] == "PASS")
    check("R29 cognitive: overload FAILs",
          bad["status"] == "FAIL" and any(i["code"] == "COGNITIVE_OVERLOAD"
                                          for i in bad["issues"]))
    check("R29 load_index numeric", isinstance(load_index(_good_beat())[0], float))


def t_registry():
    from spec_audit import RULES, registry_report, run_all
    rep = registry_report()
    check("R42 registry: 43 entries (0..42)", len(RULES) == 43)
    check("registry >=20 rules wired", rep["wired"] >= 20)
    r = run_all(_good_plan())
    check("registry run_all executes gates", r["rules_run"] >= 8)
    check("registry run_all good plan PASS", r["status"] == "PASS")


def main():
    print("== SPEC-TEST (v7.5 behavior spec) ==")
    for fn in (t_hierarchy, t_continuity, t_anchor, t_negative_space, t_budget,
               t_family, t_style_lock, t_anti_ppt, t_cognitive, t_registry):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            _FAIL.append(fn.__name__ + ":EXC")
            print("  FAIL  %s raised %r" % (fn.__name__, e))
    print("\n== SUMMARY: %d passed, %d failed ==" % (len(_PASS), len(_FAIL)))
    if _FAIL:
        print("FAILED:", ", ".join(_FAIL))
        return 1
    print("SPEC-TEST VERIFIED \u2714")
    return 0


if __name__ == "__main__":
    sys.exit(main())
