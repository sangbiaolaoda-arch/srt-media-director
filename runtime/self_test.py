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
        decor = [e for e in b["elements"] if e["type"] == "decor"]
        assert len(decor) >= 3, (b["beat_id"], len(decor))   # v4.4：每拍≥3 图形要素


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
