"""Composition planner, reference frames and compiler gates."""
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


@gate("4. 构图求解（门禁通过 / 拒绝猜坐标）")
def g4():
    _, dsl = _example_dsl()
    _, _, _, audit = composition_planner.plan(dsl)
    assert audit["status"] == "PASS", audit
    bad = {"beats": [{
        "beat_id": "beat_99", "start_sec": 0.0, "end_sec": 3.0,
        "strategy": "single_focus", "motion_policy": "required",
        "visual_claim": "x", "relations": [], "camera": {}, "carry_over": [],
        "elements": [
            {"id": "b99_hero", "slot": "hero", "type": "motif",
             "role": "primary", "motif": "phone"},
            {"id": "b99_oops", "slot": "nope", "type": "text",
             "role": "support", "text": "x", "size": "note"},
        ]}]}
    try:
        composition_planner.plan(bad)
        raise AssertionError("expected LayoutIntentIncomplete")
    except composition_planner.LayoutIntentIncomplete:
        pass


@gate("16. 参考帧构图语法（规则驱动：复现参考帧 + 泛化到新构图，非照抄）")
def g16():
    import ref_frame as R
    # (a) 规则必须能**精确复现**参考帧：cols(3) → x=[48,265,482]，列宽 150
    c3 = R.cols(3)
    assert [round(x) for x, _ in c3] == [48, 265, 482], c3
    assert abs(c3[0][1] - 150) < 0.5, c3
    c2 = R.cols(2, gap=32)
    assert [round(x) for x, _ in c2] == [48, 356], c2
    assert abs(c2[0][1] - 276) < 0.5, c2
    # (b) 规则必须能**外推**到参考帧没画过的列数（2/4/5 列：非重叠、贴版心）
    for n in (2, 4, 5):
        cc = R.cols(n)
        assert len(cc) == n, (n, cc)
        assert abs(cc[0][0] - R.MARGIN) < 0.5, (n, cc)
        assert abs((cc[-1][0] + cc[-1][1]) - (R.CANVAS_W - R.MARGIN)) < 1.0, (n, cc)
        for i in range(1, n):
            assert cc[i][0] > cc[i - 1][0] + cc[i - 1][1] - 0.5, (n, i, cc)
    # (c) 描边角色规则：强调 = 加粗 + 加深（primary 比 secondary 粗、色不同）
    assert R.stroke("primary")[0] > R.stroke("secondary")[0]
    assert R.stroke("primary")[1] != R.stroke("secondary")[1]
    # (d) 必须能产出参考帧**没有**的新构型，且仍是合法图层规范
    quad = R.frame_quadrants("四种代价", [
        ("通知", lambda cx, cy: R.icon_bell(cx, cy, 0.72), False),
        ("打断", lambda cx, cy: R.icon_focus_break(cx, cy, 0.8), False),
        ("等待", lambda cx, cy: R.icon_bar_half(cx, cy, 0.8), False),
        ("回不去", lambda cx, cy: R.icon_door(cx, cy, 0.9), True)])
    line = R.frame_timeline("一次通知的时间线", [
        ("响", "", False), ("看", "", False), ("断", "", True), ("续", "", False)])
    stack = R.frame_stack("三件事", [
        ("关通知", "", True), ("放远", "", False), ("回来", "", False)])
    for name, spec in (("quadrants", quad), ("timeline", line), ("stack", stack)):
        issues = R.audit_spec(spec)
        assert issues == [], (name, issues)
        assert R.count_accent(spec) <= 1, (name, R.count_accent(spec))
    # (e) 强调预算：参考帧系（hero / compare）必须恰好一次
    hero = R.frame_hero("为什么总在分心？", "注意力被反复打断",
                        R.icon_phone(500, 200, 0.9, badge=3), (440, 80, 136, 236))
    cmp_ = R.frame_compare(
        "离手机远一点",
        {"label": "在手边", "bar": 54, "bar_accent": False,
         "icon_inner": R.icon_phone(246, 238, 0.24), "icon_box": (226, 206, 44, 68)},
        {"label": "在另一房间", "bar": 130, "bar_accent": True,
         "icon_inner": R.icon_door(562, 245, 1.0), "icon_box": (534, 208, 60, 76)})
    assert R.count_accent(hero) == 1, R.count_accent(hero)
    assert R.count_accent(cmp_) == 1, R.count_accent(cmp_)
    for name, spec in (("hero", hero), ("compare", cmp_)):
        assert R.audit_spec(spec) == [], (name, R.audit_spec(spec))


@gate("18. 构图编译器：意图→几何（语法 1:N 实现，坐标来自规则由 Runtime 决定）")
def g18():
    import ref_frame as R
    import visual_grammar as VG
    import composition_compiler as CC
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
    spec, meta = CC.compile_intent(right)
    assert meta["issues"] == [], meta["issues"]
    assert meta["realization"] == "accum_trajectory_threshold", meta
    assert R.audit_spec(spec) == [], R.audit_spec(spec)
    assert R.count_accent(spec) == 1, R.count_accent(spec)
    # 语法到实现是 1:N：contrast 走的是不同实现（不是「语法==模板」）
    contrast = {"beat_id": "b3", "visual_claim": "near_vs_far", "grammar": ["contrast"],
                "focal_point": "far",
                "relationship": [{"from": "near", "relation": "contrast_with", "to": "far"}],
                "density": 0.45, "silence": False, "motion_intent": "contrast_then_focus",
                "entities": ["near", "far"]}
    spec2, meta2 = CC.compile_intent(contrast)
    assert meta2["issues"] == [], meta2["issues"]
    assert meta2["realization"] != meta["realization"], (meta2, meta)
    assert R.count_accent(spec2) == 1
    # 每个语法操作都必须有实现映射（Runtime 有视觉语言可画）
    for op in VG.GRAMMAR_OPS:
        assert op in CC.GRAMMAR_REALIZATION, op
    # silence 让 Runtime 收敛到更少槽位（Runtime 决定画多少，不是 Agent）
    quiet = dict(contrast); quiet["silence"] = True
    qspec, qmeta = CC.compile_intent(quiet)
    assert R.audit_spec(qspec) == [], R.audit_spec(qspec)
