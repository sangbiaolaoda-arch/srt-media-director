"""Visual grammar + necessity gates."""
import json  # noqa: F401
import os  # noqa: F401
import shutil  # noqa: F401
import sys  # noqa: F401
import tempfile  # noqa: F401

from gate_lib import (  # noqa: F401
    GATES, gate, RUNTIME, ROOT, EXAMPLE_SRT, EXAMPLE_OVERRIDES,
    _example_beats, _example_dsl, pytest_approx,
    _MOTION_TRUTH_DIRS, _EASE_FINGERPRINTS, _MAT_FINGERPRINTS,
)

import beat_planner  # noqa: F401
import composition_planner  # noqa: F401
import entrance_planner  # noqa: F401
import html_adapter  # noqa: F401
import pipeline  # noqa: F401
import raster_renderer  # noqa: F401
import srt_parser  # noqa: F401
import svg_art  # noqa: F401
import visual_director  # noqa: F401


@gate("13. 视觉语法（抽象语法替代素材名：causality/contrast/progression…）")
def g13():
    import visual_grammar
    _, dsl = _example_dsl()
    audit = visual_grammar.audit(dsl)
    assert audit["status"] == "PASS", audit["issues"]
    for b in dsl["beats"]:
        ops = b["grammar_ops"]
        assert ops, b["beat_id"]
        assert all(o in visual_grammar.GRAMMAR_OPS for o in ops), (b["beat_id"], ops)
    # 同一语法必须多于一种表层实现，否则语法退化成素材名
    for op, surfaces in visual_grammar.GRAMMAR_SURFACES.items():
        assert len(surfaces) >= 2, (op, surfaces)
    assert visual_grammar.relation_to_grammar("answer_to") == "causality"
    assert visual_grammar.relation_to_grammar("concession") == "contrast"


@gate("15. 视觉必要性（元素须能被『删除是否减弱命题』论证）")
def g15():
    import visual_necessity
    _, dsl = _example_dsl()
    audit = visual_necessity.audit(dsl)
    assert audit["status"] == "PASS", audit["issues"]
    for b in audit["beats"]:
        levels = {e["necessity"] for e in b["elements"]}
        assert levels <= set(visual_necessity.NECESSITY_LEVELS), (b["beat_id"], levels)
        assert "required" in levels, b["beat_id"]   # 每拍必有承载命题的主元素
    # 负例：既非氛围、也不承载任何意义的孤立元素应被判 UNJUSTIFIED
    bad = {"beats": [{"beat_id": "b", "narration": "x", "relations": [],
            "elements": [
                {"id": "b_p", "slot": "hero", "type": "motif", "role": "primary",
                 "motif": "target"},
                {"id": "b_z", "slot": "z", "type": "shape", "role": "support"}]}]}
    ba = visual_necessity.audit(bad)
    assert ba["status"] == "FAIL", ba
