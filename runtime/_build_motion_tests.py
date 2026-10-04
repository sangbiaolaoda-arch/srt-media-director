"""_build_motion_tests.py — Motion Compiler 验收：3 个不同 Visual Grammar 案例
+ 7 个验收场景，全部经 Motion Planner → Validator → Playwright 真实渲染 PNG。

产出 /mnt/cos/artifacts/motion/：
  case_branching_*.png / case_causality_*.png / case_accumulation_*.png  逐时刻帧
  motion-cases.png        三案例入场过程联系表
  motion-report.json      决策 + 覆盖度 + 反PPT + 验收结论
  motion-answer.md        回答 10 问
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from motion.motion_planner import compile_plan, MotionPlanner
from motion.validator import validate_motion, coverage, AntiPPTChecker
from motion.render import render_frames, beat_html
from motion.motion_report import explain
from motion.continuity import link_beats

OUT = "/mnt/cos/artifacts/motion"
os.makedirs(OUT, exist_ok=True)
W, H = 680, 382


def E(i, t, role, box, label=None, **kw):
    d = {"id": i, "type": t, "semantic_role": role, "box": list(box),
         "label": label or i, "visible": True}
    d.update(kw)
    return d


# ---------------------------------------------------------------- 三个语法案例
def case_branching():
    """grammar=branching：选择越多，决策越难。"""
    els = [
        E("bg", "decor", "background", (8, 8, 664, 366)),
        E("title", "text", "supporting", (40, 26, 260, 34), "选择越多，决策越难"),
        E("center", "motif", "focal", (300, 150, 90, 70), "决策"),
        E("opt_a", "motif", "supporting", (60, 92, 84, 56), "选项A"),
        E("opt_b", "motif", "supporting", (60, 232, 84, 56), "选项B"),
        E("opt_c", "motif", "supporting", (536, 92, 84, 56), "选项C"),
        E("opt_d", "motif", "supporting", (536, 232, 84, 56), "选项D"),
        E("lnk_a", "connector", "relationship", (150, 168, 146, 12)),
        E("lnk_b", "connector", "relationship", (150, 210, 146, 12)),
        E("lnk_c", "connector", "relationship", (394, 168, 140, 12)),
        E("lnk_d", "connector", "relationship", (394, 210, 140, 12)),
        E("cap", "text", "annotation", (200, 320, 280, 24), "分支逐渐产生"),
    ]
    rels = [{"from": "center", "type": "flow_to", "to": "lnk_a"},
            {"from": "center", "type": "flow_to", "to": "lnk_c"}]
    return {"beat_id": "branching", "start_sec": 0, "end_sec": 4.5, "grammar": ["branching"],
            "focal_point": "center", "density": 0.6, "palette": "cold",
            "strategy": "center_cluster", "elements": els, "relations": rels}


def case_causality():
    """grammar=causality：一次通知，导致整段专注中断。"""
    els = [
        E("bg", "decor", "background", (8, 8, 664, 366)),
        E("cause", "motif", "focal", (60, 150, 130, 80), "一次通知"),
        E("link", "connector", "relationship", (196, 186, 150, 12)),
        E("effect", "motif", "supporting", (352, 150, 130, 80), "专注中断"),
        E("note", "text", "annotation", (352, 250, 250, 26), "滑点后 23 分钟才恢复"),
        E("foot", "text", "label", (60, 300, 300, 24), "打断 → 偏离 → 恢复"),
    ]
    rels = [{"from": "cause", "type": "causes", "to": "effect"}]
    return {"beat_id": "causality", "start_sec": 4.5, "end_sec": 9.0, "grammar": ["causality"],
            "focal_point": "cause", "density": 0.5, "palette": "warm",
            "strategy": "cause_effect", "elements": els, "relations": rels}


def case_accumulation():
    """grammar=accumulation：问题不断累积。"""
    els = [
        E("bg", "decor", "background", (8, 8, 664, 366)),
        E("seed", "motif", "focal", (40, 150, 96, 64), "起点"),
        E("s1", "motif", "supporting", (170, 96, 96, 52), "累积1"),
        E("s2", "motif", "supporting", (170, 210, 96, 52), "累积2"),
        E("s3", "motif", "supporting", (300, 96, 96, 52), "累积3"),
        E("s4", "motif", "supporting", (300, 210, 96, 52), "累积4"),
        E("bar", "chart", "data", (440, 150, 180, 64), "总量"),
        E("cap", "text", "annotation", (440, 250, 200, 24), "越积越多"),
    ]
    rels = [{"from": "seed", "type": "flow_to", "to": "s1"},
            {"from": "s1", "type": "flow_to", "to": "s2"}]
    return {"beat_id": "accumulation", "start_sec": 9.0, "end_sec": 13.5,
            "grammar": ["accumulation"], "focal_point": "seed", "density": 0.6,
            "palette": "calm", "strategy": "left_to_right_flow",
            "elements": els, "relations": rels}


CASES = {"branching": case_branching(), "causality": case_causality(),
         "accumulation": case_accumulation()}


def contact_sheet(rows, out, cols=6, tw=320, th=180):
    gap = 10
    rr = len(rows)
    sh = Image.new("RGB", (cols * tw + (cols + 1) * gap, rr * th + (rr + 1) * gap), (245, 245, 243))
    dr = ImageDraw.Draw(sh)
    for r, (lab, paths) in enumerate(rows):
        y = gap + r * (th + gap)
        dr.text((gap + 4, y - 9), lab, fill=(20, 20, 20))
        for c, p in enumerate(paths):
            x = gap + c * (tw + gap)
            im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
            sh.paste(im, (x, y))
            dr.rectangle([x - 1, y - 1, x + tw, y + th], outline=(200, 200, 195))
    sh.save(out, quality=92)
    return sh.size


def main():
    report = {"cases": {}, "acceptance": {}, "schema": "MotionPolicy v1"}
    sheets = []

    # ---------------- 三个语法案例：编译 + 校验 + 真实渲染 ----------------
    for name, beat in CASES.items():
        dsl = {"beats": [beat]}
        plan = compile_plan(dsl)
        val = validate_motion(plan)
        bp = plan["beats"][0]
        times = [0.2, 0.6, 1.0, 1.6, 2.4, 3.4]
        paths = render_frames(bp, os.path.join(OUT, name), times)
        print("\n=== CASE %s ===" % name)
        print(explain(plan))
        print("validate:", val["status"], "coverage=%.2f" % val["motion_coverage"],
              "missing=%d static=%d moving=%d" % (val["motion_missing"],
              val["static_explicit"], val["moving"]))
        if val["warnings"]:
            for w in val["warnings"]:
                print("   warn", w["code"], w["msg"])
        report["cases"][name] = {
            "grammar": beat["grammar"], "status": val["status"],
            "coverage": val["motion_coverage"], "missing": val["motion_missing"],
            "static_explicit": val["static_explicit"], "moving": val["moving"],
            "warnings": [w["code"] for w in val["warnings"]],
            "elements": [{"id": e["id"], "role": e["semantic_role"],
                          "motion": e["motion_policy"]["type"],
                          "source": e["motion_policy"]["source"],
                          "delay": e["motion_policy"]["delay"],
                          "duration": e["motion_policy"]["duration"],
                          "reason": e["motion_policy"]["reason"]}
                         for e in bp["elements"]],
        }
        sheets.append(("%s  [%s]  " % (name, beat["grammar"][0]) +
                       "  ".join("t=%.1f" % t for t in times), paths))

    sheet_path = os.path.join("/mnt/cos/artifacts", "motion-cases.png")
    size = contact_sheet(sheets, sheet_path)
    report["case_contact_sheet"] = sheet_path

    # ---------------- 7 个验收场景 ----------------
    A = report["acceptance"]

    # Case 1: Agent 完全不写动画
    b1 = {"beat_id": "c1", "start_sec": 0, "end_sec": 4, "grammar": ["establish"],
          "focal_point": "hero", "density": 0.5,
          "elements": [E("hero", "motif", "focal", (280, 140, 120, 90), "核心"),
                       E("sup", "text", "supporting", (200, 260, 280, 30), "说明"),
                       E("bg", "decor", "background", (0, 0, 680, 382))]}
    p1 = compile_plan({"beats": [b1]}); v1 = validate_motion(p1)
    A["case1_agent_no_animation"] = {"status": v1["status"], "coverage": v1["motion_coverage"],
                                     "all_have_policy": v1["motion_missing"] == 0,
                                     "decisions": {e["id"]: e["motion_policy"]["type"] for e in p1["beats"][0]["elements"]}}

    # Case 2: Agent 只给 motion_intent
    b2 = {"beat_id": "c2", "start_sec": 0, "end_sec": 4, "grammar": ["emphasis"],
          "focal_point": "hero",
          "elements": [E("hero", "motif", "focal", (280, 140, 120, 90), "核心", motion_intent="reveal"),
                       E("sup", "text", "supporting", (200, 260, 280, 30), "说明", motion_intent="slide")]}
    p2 = compile_plan({"beats": [b2]}); v2 = validate_motion(p2)
    A["case2_intent_only"] = {"status": v2["status"],
                              "decisions": {e["id"]: (e["motion_policy"]["type"], e["motion_policy"]["source"])
                                            for e in p2["beats"][0]["elements"]}}

    # Case 3: Agent 明确 static
    b3 = {"beat_id": "c3", "start_sec": 0, "end_sec": 4, "grammar": ["establish"],
          "focal_point": "hero",
          "elements": [E("hero", "motif", "focal", (280, 140, 120, 90), "核心",
                         motion_policy={"type": "static", "reason": "保留为稳定参照"}),
                       E("grid", "group", "decoration", (30, 30, 620, 320), "网格",
                         motion_policy={"type": "static"})]}
    p3 = compile_plan({"beats": [b3]}); v3 = validate_motion(p3)
    A["case3_explicit_static"] = {"status": v3["status"], "static_explicit": v3["static_explicit"],
                                  "decisions": {e["id"]: e["motion_policy"]["type"] for e in p3["beats"][0]["elements"]}}

    # Case 4: 元素完全无 motion_policy → 自动补全
    b4 = {"beat_id": "c4", "start_sec": 0, "end_sec": 4, "grammar": ["hierarchy"],
          "focal_point": "a",
          "elements": [E("a", "motif", "focal", (100, 140, 120, 90), "A"),
                       E("b", "text", "supporting", (300, 150, 200, 30), "B")]}
    p4 = compile_plan({"beats": [b4]})
    # 人为抹掉所有 motion_policy，模拟「进入 RenderPlan 却缺失」
    for bp in p4["beats"]:
        for e in bp["elements"]:
            e["motion_policy"] = None
    missing_before = coverage(p4)["motion_missing"]
    v4 = validate_motion(p4, autocomp=True)
    A["case4_missing_autofill"] = {"missing_before": missing_before,
                                   "autocompleted": v4["autocompleted"],
                                   "status_after": v4["status"],
                                   "coverage_after": v4["motion_coverage"]}

    # Case 5: 所有元素都 fade → REPETITIVE_MOTION
    b5 = {"beat_id": "c5", "start_sec": 0, "end_sec": 4, "grammar": ["establish"],
          "focal_point": "e0",
          "elements": [E("e%d" % i, "motif", "focal" if i == 0 else "supporting",
                         (60 + i * 90, 150, 80, 60), "E%d" % i,
                         motion_policy={"type": "fade"}) for i in range(6)]}
    v5 = validate_motion(compile_plan({"beats": [b5]}))
    A["case5_all_fade"] = {"status": v5["status"],
                           "warnings": [w["code"] for w in v5["warnings"]],
                           "detected_repetitive": any(w["code"] == "REPETITIVE_MOTION" for w in v5["warnings"])}

    # Case 6: 10 个元素同时运动 → 密度/并发警告
    b6 = {"beat_id": "c6", "start_sec": 0, "end_sec": 4, "grammar": ["abstract"],
          "focal_point": "e0",
          "elements": [E("e%d" % i, "motif", "focal" if i == 0 else "supporting",
                         (40 + (i % 5) * 120, 120 + (i // 5) * 120, 90, 70), "E%d" % i,
                         motion_policy={"type": ["emerge", "scale", "slide", "draw", "grow"][i % 5]})
                       for i in range(10)]}
    v6 = validate_motion(compile_plan({"beats": [b6]}))
    A["case6_ten_simultaneous"] = {"status": v6["status"],
                                   "warnings": [w["code"] for w in v6["warnings"]],
                                   "detected_density": any(w["code"] in ("MOTION_DENSITY_TOO_HIGH",
                                                       "EXCESSIVE_MOTION", "TOO_MANY_SIMULTANEOUS_MOTIONS")
                                                           for w in v6["warnings"])}

    # Case 7: 跨 Beat 连续（carry_over / transform）
    bA = {"beat_id": "s1", "start_sec": 0, "end_sec": 4, "grammar": ["establish"],
          "focal_point": "decision",
          "elements": [E("decision", "motif", "focal", (280, 150, 120, 80), "决策"),
                       E("ctx", "text", "supporting", (200, 260, 280, 30), "上下文")]}
    bB = {"beat_id": "s2", "start_sec": 4, "end_sec": 8, "grammar": ["emphasis"],
          "focal_point": "decision",
          "elements": [E("decision", "motif", "focal", (260, 130, 160, 120), "决策", value="expanded"),
                       E("new", "text", "supporting", (200, 280, 280, 30), "追加信息")]}
    p7 = compile_plan({"beats": [bA, bB]})
    val7 = validate_motion(p7)
    A["case7_continuity"] = {
        "status": val7["status"],
        "beat1_decision": p7["beats"][0]["elements"][0]["motion_policy"]["type"],
        "beat2_decision": p7["beats"][1]["elements"][0]["motion_policy"]["type"],
        "beat2_decision_source": p7["beats"][1]["elements"][0]["motion_policy"]["source"],
        "beat2_new": p7["beats"][1]["elements"][1]["motion_policy"]["type"],
        "reenters_instead_of_carry": p7["beats"][1]["elements"][0]["motion_policy"]["type"] not in
            ("carry_over", "continue", "transform", "static"),
    }

    with open(os.path.join(OUT, "motion-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n===== 验收汇总 =====")
    for k, v in A.items():
        print(" ", k, "->", json.dumps(v, ensure_ascii=False)[:200])
    print("\ncontact sheet:", sheet_path, size)


if __name__ == "__main__":
    main()
