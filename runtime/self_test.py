"""Runtime self-test — the Bootstrap Gate.

    python runtime/self_test.py

The runtime may be created by an agent, but it may never declare itself
correct. This suite is the machine evidence. Exit code 0 = VERIFIED.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beat_planner  # noqa: E402
import composition_planner  # noqa: E402
import entrance_planner  # noqa: E402
import html_adapter  # noqa: E402
import pipeline  # noqa: E402
import raster_renderer  # noqa: E402
import srt_parser  # noqa: E402
import svg_art  # noqa: E402
import visual_director  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_SRT = os.path.join(ROOT, "examples", "minimal", "attention.srt")
EXAMPLE_OVERRIDES = os.path.join(ROOT, "examples", "minimal",
                                 "director_overrides.json")

GATES = []


def gate(name):
    def deco(fn):
        GATES.append((name, fn))
        return fn
    return deco


def _example_beats():
    analysis = srt_parser.analyze(EXAMPLE_SRT)
    return analysis, beat_planner.plan_beats(analysis["cues"])


def _example_dsl():
    _, beats = _example_beats()
    ov = visual_director.load_overrides(EXAMPLE_OVERRIDES)
    vplan, dsl = visual_director.direct(beats, ov)
    return vplan, dsl


@gate("1. SRT 解析（时间真值）")
def g1():
    a = srt_parser.analyze(EXAMPLE_SRT)
    assert not a["errors"], a["errors"]
    assert len(a["cues"]) == 8, len(a["cues"])
    starts = [c["start"] for c in a["cues"]]
    assert starts == sorted(starts)
    assert abs(a["total_duration_sec"] - 38.0) < 0.01, a["total_duration_sec"]


@gate("2. Beat 基线（不丢字幕 / 不拆语义单位）")
def g2():
    a, beats = _example_beats()
    assert 4 <= len(beats) <= 10, len(beats)
    covered = []
    for b in beats:
        covered.extend(range(b["cue_range"][0], b["cue_range"][1] + 1))
    assert covered == list(range(1, 9)), covered
    assert "".join(b["narration"] for b in beats) == "".join(
        c["text"] for c in a["cues"])
    # v4.3 语义检索：问答/让步/因果对必须同拍（硬约束不得被切开）
    synth = [{"id": i + 1, "start": i * 2.0, "end": i * 2.0 + 1.8, "text": t}
             for i, t in enumerate([
                 "你这么拼到底是想赢给谁看",          # 1 问句
                 "你大概会说你是为了自己",            # 2 答句（紧随问句）
                 "你真的很拼很努力每一天",            # 3 铺垫
                 "可它总会在某个晚上回来",            # 4 转折（让步）
                 "时间只有一个方向不可逆",            # 5 陈述
                 "所以你要的到底是什么",              # 6 结论（因果）
                 "签字那一刻你等了很久",              # 7
                 "那个字也可以自己签",                # 8
             ])]
    sb = beat_planner.plan_beats(synth)

    def _bid(cid):
        return next(b["beat_id"] for b in sb
                    if b["cue_range"][0] <= cid <= b["cue_range"][1])
    assert _bid(1) == _bid(2), sb      # 问答硬约束：问句与答句同拍
    assert _bid(3) == _bid(4), sb      # 让步硬约束：铺垫与转折同拍
    assert _bid(5) == _bid(6), sb      # 因果硬约束：陈述与所以同拍
    assert any(p["type"] == "answer_to"
               for b in sb for p in b["semantic_pairs"]), \
        [b["semantic_pairs"] for b in sb]
    assert all(b["duration_sec"] <= beat_planner.MAX_D * 1.75 + 0.01
               for b in sb), [b["duration_sec"] for b in sb]  # 硬约束组也不许超长


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
        # P0②：不再用「每拍≥N 图形要素」硬门禁逼导演堆料；元素是否该存在，
        # 交给必要性审计（g15）——数量是结果，不是约束。画面该密则密、该简则简。


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


@gate("5. 入场编排（节奏预算 / handoff / G 门禁）")
def g5():
    _, dsl = _example_dsl()
    entrance = entrance_planner.plan(dsl)
    audit = entrance_planner.audit(entrance)
    assert audit["status"] == "PASS", audit["issues"]
    for b in entrance["beats"]:
        assert b["pacing"]["last_meaningful_event_ratio"] >= 0.8, b["beat_id"]
        assert b["handoff"], b["beat_id"]
    # v4.1：每元素 lifecycle —— enter.after 依赖 / 注解必退场 / 拍尾要干净
    for b in entrance["beats"]:
        life = b["lifecycle"]
        for cue in b["cues"]:
            for eid in cue["elements"]:
                assert "after" in life[eid]["enter"], (b["beat_id"], eid)
        for eid, lc in life.items():
            if "_note" in eid:
                assert lc["exit"], (b["beat_id"], eid)
        assert (any(lc["exit"] for lc in life.values())
                or any(lc["enter"]["motion"] == "inherit"
                       for lc in life.values())
                or b["handoff"]["type"] == "final_hold"), b["beat_id"]
    # v4.1：合成交接链——相邻拍共享 motif → 下一拍 inherit 免重入、本拍免退场
    synth = {"beats": []}
    for i, (s0, e0) in enumerate(((0.0, 4.0), (4.0, 8.0))):
        bid = "beat_%02d" % (i + 1)
        synth["beats"].append({
            "beat_id": bid, "start_sec": s0, "end_sec": e0,
            "strategy": "single_focus", "motion_policy": "required",
            "visual_claim": "x", "relations": [], "camera": {}, "carry_over": [],
            "elements": [
                {"id": "%s_hero" % bid, "slot": "hero", "type": "motif",
                 "role": "primary", "motif": "shield", "art": "shield",
                 "color_role": "positive"},
                {"id": "%s_note" % bid, "slot": "note", "type": "text",
                 "role": "support", "text": "n", "size": "note",
                 "color_role": "neutral"},
            ]})
    ent2 = entrance_planner.plan(synth)
    assert ent2["beats"][0]["handoff"]["type"] == "carry_over"
    assert ent2["beats"][0]["lifecycle"]["beat_01_hero"]["exit"] is None
    lc2 = ent2["beats"][1]["lifecycle"]["beat_02_hero"]
    assert lc2["enter"]["motion"] == "inherit" and lc2["exit"] is None
    a2 = entrance_planner.audit(ent2)
    assert a2["status"] == "PASS", a2["issues"]


@gate("6. 光栅探针（真实帧 / 墨水量 / 颜色数）")
def g6():
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    tmp = tempfile.mkdtemp()
    try:
        report = raster_renderer.render_previews(dsl, render_plan, entrance, tmp)
        assert len(report) == len(dsl["beats"])
        for bid, r in report.items():
            assert 0.005 <= r["ink_ratio"] <= 0.65, (bid, r["ink_ratio"])
            assert r["distinct_colors"] >= 12, (bid, r["distinct_colors"])
            assert os.path.exists(r["frame"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@gate("7. HTML 适配器（编译产物包含全部 beat）")
def g7():
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    tmp = tempfile.mkdtemp()
    try:
        path = html_adapter.compile(dsl, render_plan, entrance, "self-test", tmp)
        html = open(path, encoding="utf-8").read()
        for b in dsl["beats"]:
            assert b["beat_id"] in html
        assert "requestAnimationFrame" in html
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@gate("8. 端到端流水线（30s 样例 / 全部产物 / 校验 PASS）")
def g8():
    import make_sample
    tmp = tempfile.mkdtemp()
    try:
        trimmed = os.path.join(tmp, "trimmed.srt")
        make_sample.trim_srt(EXAMPLE_SRT, trimmed, 30.0)
        report = pipeline.run(trimmed, os.path.join(tmp, "out"),
                              overrides_path=EXAMPLE_OVERRIDES,
                              render_previews=True, log=lambda *a: None)
        assert report["status"] == "PASS", json.dumps(report["issues"],
                                                      ensure_ascii=False)
        work = os.path.join(tmp, "out", "work")
        for f in ("srt-analysis.json", "beat-plan.json", "visual-plan.json",
                  "visual-dsl.json", "render-plan.json", "layout-intent.json",
                  "content-footprint.json", "layout-audit.json",
                  "entrance-plan.json", "validation-report.json"):
            assert os.path.exists(os.path.join(work, f)), f
        assert os.path.exists(os.path.join(tmp, "out", "film", "index.html"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@gate("9. 生成后契约（end_state / transition 三类型 / hold 下限 / 视线路径 / ambient）")
def g9():
    import contracts
    from common import CANVAS_W, CANVAS_H
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    cbeats = contracts.derive(dsl, render_plan, entrance, CANVAS_W, CANVAS_H)
    audit = contracts.validate(dsl, cbeats, CANVAS_W, CANVAS_H)
    assert audit["status"] == "PASS", audit["issues"]
    for i, c in enumerate(cbeats):
        es = c["end_state"]
        assert set(es) >= {"visible", "positions", "hold_ms"}, c["beat_id"]
        assert len(c["attention_path"]) <= 4, c["beat_id"]
        assert c["primary"] in c["attention_path"], (c["beat_id"], c["primary"])
        tr = c["transition_in"]
        assert tr["type"] in contracts.TRANSITION_TYPES, tr
        assert tr["reason"], c["beat_id"]
        if i > 0 and tr["type"] == "dissolve":
            assert tr["carried"], c["beat_id"]
        if i > 0 and tr["type"] == "cut":
            assert tr.get("composition_changed"), c["beat_id"]
    # 负例：hold 过短应被阻断
    bad = {"beats": [dict(dsl["beats"][0])]}
    bad_c = [{"beat_id": dsl["beats"][0]["beat_id"], "primary": None,
              "attention_path": [], "ambient": {},
              "end_state": {"visible": [], "positions": {}, "hold_ms": 0},
              "transition_in": {"type": "cut", "carried": [], "reason": "x"}}]
    ba = contracts.validate(bad, bad_c, CANVAS_W, CANVAS_H)
    assert any(i["code"] == "HOLD_TOO_SHORT" for i in ba["issues"]), ba["issues"]


@gate("10. 风格锁定（token 外颜色/线宽/字体报错）")
def g10():
    import style_guard
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    tmp = tempfile.mkdtemp()
    try:
        path = html_adapter.compile(dsl, render_plan, entrance, "self-test", tmp)
        audit = style_guard.scan(ROOT, path)
        assert audit["status"] == "PASS", audit["issues"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@gate("11. 语义断句（同拍拼接不粘连 / 硬约束不可拆）")
def g11():
    # 无标点拼接必须补逗号，禁止两句话首尾粘连
    j = beat_planner._join_texts(["万般皆是命，半点不由人", "说这句话的人", "其实很努力"])
    assert "人说这句话的人" not in j, j
    assert "，" in j, j
    a, beats = _example_beats()
    assert "".join(b["narration"] for b in beats) == "".join(
        c["text"] for c in a["cues"]).replace("\n", "")
    # 每拍 narration 内部不应出现「句号/问号/感叹号 + 无标点直接接字」
    for b in beats:
        n = b["narration"]
        assert "。说" not in n and "？说" not in n, (b["beat_id"], n)


@gate("12. 故障路由（症状 → 修复层 → 单变量预算）")
def g12():
    import repair_routing
    r = repair_routing.route({"code": "CARRY_NOT_IN_PREV", "msg": "x"})
    assert r["layer"] == "transition", r
    r = repair_routing.route({"code": "STYLE_COLOR", "msg": "x"})
    assert r["layer"] == "token", r
    r = repair_routing.route({"code": "HOLD_TOO_SHORT", "msg": "x"})
    assert r["layer"] == "contract", r
    b = repair_routing.RepairBudget(budget=2)
    assert b.attempt("beat_01") and b.attempt("beat_01")
    assert not b.attempt("beat_01"), "第 3 次应超预算"
    assert "beat_01" in b.exhausted()


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


@gate("14. Style Bible（视频级视觉人格随内容推导，非固定风格）")
def g14():
    import style_bible
    vp, dsl = _example_dsl()
    assert "style_bible" in vp["global_visual_grammar"]
    _, beats = _example_beats()
    bible = style_bible.derive_style_bible(beats)
    v = style_bible.validate_bible(bible)
    assert v["status"] == "PASS", v["issues"]
    for k in style_bible.REQUIRED_KEYS:
        assert k in bible, k
    # 人格由内容推导：更长句子的内容应得出非 sparse 的 density
    b2 = style_bible.derive_style_bible(
        [{"narration": "这是一句明显更长的叙述文本用于改变密度档位", "semantic_role": "explanation"}])
    assert b2["density"] in style_bible.DENSITIES


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


@gate("19. Runtime 六包架构：director/compiler/render/validation/primitives/schemas 可导入且接线")
def g19():
    import os
    # (a) 目标架构的六个包必须存在且可导入
    import director, compiler, render, validation, primitives
    import schemas as SCH
    root = os.path.dirname(os.path.abspath(__file__))
    for pkg in ("director", "compiler", "render", "validation", "primitives", "schemas"):
        assert os.path.isdir(os.path.join(root, pkg)), "缺包 " + pkg
    # (b) 目标文件布局（用户给的结构）
    want = {
        "director": ["visual_intent.py", "grammar.py", "relationship.py"],
        "compiler": ["composition.py", "constraints.py", "layout.py", "svg_compiler.py"],
        "render": ["html_renderer.py", "playwright_renderer.py", "screenshot.py"],
        "validation": ["geometry.py", "typography.py", "safe_area.py", "visual_regression.py"],
        "primitives": ["text.py", "shape.py", "path.py", "chart.py", "connector.py", "motif.py"],
        "schemas": ["visual_intent.json", "visual_plan.json", "render_plan.json"],
    }
    for pkg, files in want.items():
        for f in files:
            assert os.path.exists(os.path.join(root, pkg, f)), "缺文件 %s/%s" % (pkg, f)
    # (c) 跨包接线可用：director → compiler → render → validation
    from director import grammar as G, relationship as REL, visual_intent as VI, critic as C
    assert len(G.GRAMMAR_OPS) == 12
    assert G.unknown_ops(["contrast", "bogus"]) == ["bogus"]
    assert REL.sinks([{"from": "a", "relation": "accumulate_into", "to": "b"},
                      {"from": "b", "relation": "crosses", "to": "c"}]) == ["c"]
    assert hasattr(VI, "derive") and hasattr(VI, "validate")
    from compiler import composition as CO, constraints as CON, layout as LAY, svg_compiler as SVGC
    assert CO.coverage() and all(CO.coverage().values())        # 每个语法都有实现可画
    assert LAY.safe_area()["margin"] == __import__("ref_frame").MARGIN
    from render import screenshot as SHOT
    be = SHOT.backends()
    assert set(be) == {"playwright", "chromium", "cairosvg"}, be
    assert any(be.values()), be                                  # 至少一个后端可用（如实探测）
    from validation import geometry, typography, safe_area
    assert callable(geometry.check) and callable(typography.check) and callable(safe_area.check)
    assert SCH.available() == ["render_plan", "visual_intent", "visual_plan"], SCH.available()


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


@gate("21. Motion Runtime（语义运动不变量）")
def g21():
    """Runtime Hardening · 语义运动执行层的机器证据门禁。

    验证：① 每个 Motion Primitive 都拥有合法 Contract；
          ② Scene/Relation/State/Motion/Conflict 可端到端执行且**确定性**；
          ③ Motion Invariants 全部通过。
    """
    import motion_runtime as MR
    from motion_runtime import (MotionRuntime, SceneGraph, make, Relation,
                                audit_contracts)
    # ① 契约自检
    ac = audit_contracts()
    assert ac["status"] == "PASS", ac["issues"]
    assert ac["count"] >= 21, ac["count"]  # 21 个语义运动原语
    # ② 端到端执行（层级 + 关系 + 运动 + 冲突求解 + Camera）
    g = SceneGraph()
    g.add("group", parent="root", x=100, y=100)
    g.add("person", parent="group", x=0, y=0, w=120, h=200)
    g.add("choice", parent="root", x=600, y=200, w=140, h=60)
    rt = MotionRuntime(g)
    rt.add(make("MOVE", "group", duration=1.0, trigger="t0",
                params={"offset": (50, 0)}),
           make("FOLLOW", "person", target="choice", duration=1.0, trigger="t0",
                params={"lag": 0.2}))
    rt.add_relation(Relation(source="person", target="choice",
                             relation_type="CAUSE", lifecycle="STRENGTHEN",
                             trigger="person.activate"))
    # 确定性：相同输入必须产生完全相同的采样
    assert rt.sample(0.5) == rt.sample(0.5), "motion runtime must be deterministic"
    frames = rt.sample_frames(1.0)
    assert len(frames) >= 5, frames
    # ③ 不变量
    v = rt.validate()
    assert v["status"] == "PASS", v["failed"]
    # 冲突求解不是 last-wins：FOLLOW 位移必须保留
    tr = rt.sample(1.0)["transforms"]["person"]
    assert tr["dx"] > 50, tr


@gate("22. Motion 归一（单一 Canonical Motion，无重复真相源）")
def g22():
    """MOTION UNIFICATION · P0 的机器证据门禁。

    验证：① 唯一的 Canonical Motion 包可导入且词汇自审通过；
          ② Motion 不重复实现缓动 / 变换 —— 对 timeline.easing 与
             geometry.matrix 的委托零数值偏差；
          ③ 边界守卫证明 canonical motion 从不 import 旧生产实现；
          ④ 契约 contracts/motion_semantics.v2.json 存在且类别集合一致。
    """
    import motion_canonical as MC
    from timeline import easing as T_EASING
    from geometry import matrix as G_MATRIX

    # ① 词汇唯一真相源
    va = MC.vocabulary.audit()
    assert va["status"] == "PASS", va["issues"]
    assert va["canonical_actions"] >= 45, va["canonical_actions"]
    for n in ("fade", "rise", "pop", "inherit", "sink", "shrink",
              "MOVE", "SCALE", "ROTATE", "MORPH", "emerge", "wipe"):
        assert MC.vocabulary.is_canonical(MC.vocabulary.canonical(n)), n

    # ② 缓动 / 进度 / 变换委托零偏差
    for p in [i / 50.0 for i in range(51)]:
        assert MC.easing.evaluate("easeOutCubic", p) == \
            pytest_approx(T_EASING.evaluate("easeOutCubic", p)), p
    assert MC.progress.progress(0.5, 0.0, 2.0, "easeOutCubic") == \
        pytest_approx(T_EASING.pr(0.5, 0.0, 2.0, "easeOutCubic"))
    ch = {"dx": 3.0, "dy": -4.0, "scale": 2.0, "rotation": 30.0}
    got = MC.transform.channels_to_matrix(x=1, y=2, channels=ch)
    exp = G_MATRIX.mat_from_parts(1 + 3.0, 2 + (-4.0), 30.0, 2.0)
    for a, b in zip(got, exp):
        assert a == pytest_approx(b), (a, b)
    from motion_runtime import contracts as _C
    for key, fn in _C.EASINGS.items():
        assert fn(0.37) == pytest_approx(T_EASING.evaluate(key, 0.37)), key

    # ③ 边界守卫：不得 import 旧生产实现
    assert MC.boundary_report()["status"] == "PASS", MC.boundary_report()
    MC.assert_boundaries()

    # ④ 契约存在且类别一致
    import json
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "contracts", "motion_semantics.v2.json")) as fh:
        c = json.load(fh)
    assert c["contract_id"] == "motion_semantics.v2"
    for cat in c["categories"]:
        if not cat.startswith("_"):
            assert cat in MC.vocabulary.CATEGORIES, cat


def pytest_approx(x, tol=1e-9):
    """无需引入 pytest 的近似比较（self_test 是独立可执行脚本）。"""
    class _A:
        def __eq__(self, other):
            return abs(other - x) <= tol
    return _A()


# --- Motion canonicalization: sources allowed to hold curve/matrix math ------
_MOTION_TRUTH_DIRS = ("timeline", "observer", "motion_canonical", "geometry")
# 曲线 / 矩阵数学的“指纹”。它们只允许出现在上方的真相源目录里。
_EASE_FINGERPRINTS = (
    "1.0 - (1.0 - p)",
    "1 - (1 - p) ** 3",
    "1.70158",
    "2 * p * p",
    "def ease_out_cubic",
    "def ease_in_cubic",
    "def ease_out_back",
)
_MAT_FINGERPRINTS = (
    "a1 * a2 + c1 * b2",
    "b1 * a2 + d1 * b2",
    "cos, sin = math.cos(rad)",
)


@gate("23. Motion Canonicalization（无重复缓动 / 矩阵 / 词汇真相源）")
def g23():
    """PHASE 7 门禁：证明 Motion 已真正归一。

    ① runtime/ 下除真相源目录(timeline/observer/motion_canonical/geometry)
       外，不得再出现缓动或矩阵数学的“指纹”；
    ② scene 语义动作的 easing 必须可被唯一真相源 timeline.easing 解析；
    ③ motion registry 的 CSS 缓动同样必须可解析；
    ④ 旧生产实现不得被 canonical motion 反向依赖（边界守卫 PASS）。
    """
    root = os.path.dirname(os.path.abspath(__file__))

    offenders = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        rel = os.path.relpath(dirpath, root)
        top = rel.split(os.sep)[0]
        if top in _MOTION_TRUTH_DIRS:
            continue  # 真相源目录允许持有数学
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            if fn == os.path.basename(__file__):
                continue  # 门禁自身持有指纹字符串，不是重复实现
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            for fp in _EASE_FINGERPRINTS + _MAT_FINGERPRINTS:
                if fp in text:
                    offenders.append((os.path.join(rel, fn), fp))
    assert not offenders, "重复的缓动/矩阵数学仍存在: %r" % offenders

    # ② scene 语义动作 easing 可解析
    import scene.motion_compiler as _mc
    ea = _mc.audit_easing()
    assert ea["status"] == "PASS", ea["unknown"]

    # ③ motion registry 的 CSS 缓动可解析
    from timeline import easing as _E
    import motion.motion_registry as _mr
    for v in _mr.MOTION_PRIMITIVES.values():
        e = v.get("easing")
        assert e is None or _E.is_known(e), e

    # ④ 边界守卫
    import motion_canonical as MC
    assert MC.boundary_report()["status"] == "PASS", MC.boundary_report()


@gate("24. Procedural 归一（确定性种子 + 布局/晶格单一真相源）")
def g24():
    """PROCEDURAL NORMALIZATION · P1 的机器证据门禁。

    验证：① 唯一 Canonical Procedural 包可导入且边界守卫 PASS；
          ② 种子策略可复现且与 PYTHONHASHSEED 无关；
          ③ 生产实现不再自造 RNG / 硬编码种子（静态扫描为空）；
          ④ ref_frame 的分槽与 svg_art 的晶格已委托 canonical layout；
          ⑤ 契约 contracts/procedural_semantics.v1.json 存在且迁移映射一致。
    """
    import procedural_canonical as PC

    # ① 边界守卫：canonical procedural 只能是 stdlib 叶子
    br = PC.boundary_report()
    assert br["status"] == "PASS", br
    PC.assert_boundaries()

    # ② 确定性：默认种子与逐拍种子可复现，且不依赖 PYTHONHASHSEED
    probe = PC.audit.determinism_probe()
    assert probe["default_reproducible"], probe
    assert probe["beat_reproducible"], probe
    assert probe["hash_seed_independent"], probe
    assert PC.rng.DEFAULT_SEED == 20261003, PC.rng.DEFAULT_SEED

    # ③ 无第二个种子真相源：runtime 内（canonical 包外）不得出现 random.* / 硬编码种子
    hits = PC.audit.seed_sources()
    assert hits == [], hits

    # ④ 布局 / 晶格委托：ref_frame 必须是 canonical layout 的薄封装
    import ref_frame as _R
    from procedural_canonical import layout as _L
    assert _R.cols(3) == _L.slots(3, _R.MARGIN, _R.CONTENT_W, _R.COL_GAP)
    assert _R.rows(4, 100, 400, 20) == _L.stacks(4, 100, 400, 20)
    assert _L.lattice(3, 2, 10, 20, 5, 7) == \
        [(10, 20), (15, 20), (20, 20), (10, 27), (15, 27), (20, 27)]
    # 逐拍种子的 recipe 与旧内联 md5 零偏差（迁移 M8）
    import hashlib as _hl
    _beat = {"beat_id": "b01", "narration": "注意力被反复打断"}
    _legacy = int(_hl.md5(("%s|%s" % (_beat["beat_id"], _beat["narration"]))
                          .encode("utf-8")).hexdigest()[:8], 16)
    assert PC.rng.stable_seed(PC.rng.beat_key(_beat)) == _legacy

    # ⑤ 契约存在且映射一致
    import json as _json
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(_root, "contracts", "procedural_semantics.v1.json")) as fh:
        _c = _json.load(fh)
    assert _c["contract_id"] == "procedural_semantics.v1"
    assert set(_c["owns"]["rng"]) >= {"stable_seed", "default_rng", "rng_for_beat"}
    assert set(_c["owns"]["layout"]) >= {"slots", "stacks", "lattice"}


def main():
    print("SRT Media Director — runtime self-test")
    failures = []
    for name, fn in GATES:
        try:
            fn()
            print("  PASS  %s" % name)
        except Exception as e:  # noqa: BLE001 — 报告全部失败而非首个
            failures.append((name, repr(e)))
            print("  FAIL  %s -> %r" % (name, e))
    if failures:
        print("\nSELF-TEST FAILED: %d gate(s)" % len(failures))
        for name, err in failures:
            print("  - %s: %s" % (name, err))
        sys.exit(1)
    print("\nSELF-TEST VERIFIED ✔  (runtime may enter the directing pipeline)")


if __name__ == "__main__":
    main()
