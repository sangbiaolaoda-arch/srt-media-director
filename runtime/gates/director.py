"""Visual director, intent layer and generate->critic loop gates."""
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


@gate("3. 导演层（命题 / 强调 / 策略多样性 / R8）")
def g3():
    vplan, dsl = _example_dsl()
    strats = [b["strategy"] for b in dsl["beats"]]
    assert len(set(strats)) >= 4, strats
    for i in range(1, len(strats)):
        assert strats[i] != strats[i - 1], "R8 violated: %s" % strats
    for b in dsl["beats"]:
        assert len([e for e in b["elements"] if e["role"] == "primary"]) == 1, \
            b["beat_id"]
        assert b["visual_claim"], b["beat_id"]
    donut = [b for b in dsl["beats"] if b["strategy"] == "center_cluster"]
    assert donut and any(e.get("host") for e in donut[0]["elements"])
    for b in vplan["beats"]:
        assert b["evidence"] and b["emphasis_plan"]["candidates"] is not None
    # v4.1：SVG 画法库机器门禁（越界审计）+ 非拟人词汇表 + 每拍装饰附体
    bad_art = svg_art.audit_all()
    assert bad_art == {}, bad_art
    for b in dsl["beats"]:
        motifs = [e.get("motif") for e in b["elements"] if e["type"] == "motif"]
        assert all(m in svg_art.MOTIF_ARTS for m in motifs), (b["beat_id"], motifs)


@gate("17. 意图层：Agent 输出视觉意图而非模板选择（拒斥 strategy/像素泄漏）")
def g17():
    import intent_layer as IL
    # 用户点名的「错误方式」：模板选择器 —— 必须被拒斥
    wrong = {"strategy": "cause_effect", "template": "left_to_right_flow",
             "hero_x": 300, "hero_y": 400}
    assert IL.is_template_selector(wrong) is True
    leak = IL.template_leak_keys(wrong)
    for k in ("strategy", "template", "hero_x", "hero_y"):
        assert k in leak, (k, leak)
    codes = [i["code"] for i in IL.validate_intent(wrong)]
    assert "INTENT_TEMPLATE_LEAK" in codes, codes
    # 用户点名的「正确方式」：语义视觉意图 —— 必须通过
    right = {
        "beat_id": "b1",
        "visual_claim": "small_repeated_actions_accumulate_into_large_change",
        "grammar": ["accumulation", "trajectory", "threshold"],
        "focal_point": "trajectory",
        "relationship": [
            {"from": "small_actions", "relation": "accumulate_into", "to": "trajectory"},
            {"from": "trajectory", "relation": "crosses", "to": "threshold"}],
        "density": 0.62, "silence": False, "motion_intent": "accumulate_then_reveal",
        "entities": ["small_actions", "trajectory", "threshold"]}
    assert IL.is_template_selector(right) is False
    assert IL.validate_intent(right) == [], IL.validate_intent(right)
    # 从 beat 推导意图也必须合法（且不含任何坐标/模板键）
    beat = {"beat_id": "b2", "narration": "一个小动作反复累积，最终越过阈值",
            "semantic_role": "explanation",
            "relations": [{"from": "small_actions", "type": "causes", "to": "trajectory"}],
            "focal_point": "trajectory"}
    d = IL.derive_intent(beat)
    assert IL.validate_intent(d) == [], IL.validate_intent(d)
    assert IL.template_leak_keys(d) == [], IL.template_leak_keys(d)


@gate("20. 生成→截图→Critic→修复 闭环：PASS 前进 + FAIL 路由回上游层")
def g20():
    import tempfile
    import ref_frame as R
    import director_loop as DL
    from director import critic as C
    from compiler import constraints as CON

    good = {"beat_id": "b1", "visual_claim": "small_actions_accumulate",
            "grammar": ["accumulation", "trajectory", "threshold"],
            "focal_point": "trajectory",
            "relationship": [{"from": "small_actions", "relation": "accumulate_into", "to": "trajectory"},
                             {"from": "trajectory", "relation": "crosses", "to": "threshold"}],
            "density": 0.62, "silence": False, "motion_intent": "accumulate_then_reveal",
            "entities": ["small_actions", "trajectory", "threshold"]}
    d = tempfile.mkdtemp()
    r = DL.run_beat(good, d, max_repair=2)
    # 闭环必须真的渲染出 PNG 并 PASS（真实证据，不是纸面）
    assert r["verdict"] == "PASS", r
    assert r["png"] and os.path.exists(r["png"]), r
    assert r["backend"] in ("playwright", "chromium", "cairosvg"), r
    # 修复路由：问题码必须指回正确上游层
    assert C.route([{"code": "CRITIC_OVERCROWDED"}])["target_layer"] == "intent"
    assert C.route([{"code": "CRITIC_BLANK_FRAME"}])["target_layer"] == "intent"
    assert C.route([{"code": "GEO_OUT_OF_CANVAS"}])["target_layer"] == "layout"
    assert C.route([{"code": "SAFE_RIGHT"}])["target_layer"] == "layout"
    assert C.route([{"code": "CRITIC_PNG_UNREADABLE"}])["target_layer"] == "render"
    # 编译期约束必须拦住超支强调
    bad = {"bg": R.BG, "elements": [
        R._E("a", '<circle cx="10" cy="10" r="4" fill="%s"/>' % R.ACC, (0, 0, 40, 40), "fade", 0),
        R._E("b", '<circle cx="30" cy="30" r="4" fill="%s"/>' % R.ACC, (0, 0, 40, 40), "fade", 0)]}
    con = CON.check(bad)
    assert con["status"] == "FAIL", con
    assert any(i["code"] == "CON_ACCENT_BUDGET" for i in con["issues"]), con
    # 修复函数：过密则降密度（确定性、可复现）
    from director_loop import _auto_fix
    fixed = _auto_fix({"density": 0.8}, {"target_layer": "intent",
                                         "issue_codes": ["CRITIC_OVERCROWDED"]}, 1)
    assert fixed["density"] < 0.8, fixed
    blank = _auto_fix({"density": 0.3, "silence": True},
                      {"target_layer": "intent", "issue_codes": ["CRITIC_BLANK_FRAME"]}, 1)
    assert blank["density"] > 0.3 and blank["silence"] is False, blank
