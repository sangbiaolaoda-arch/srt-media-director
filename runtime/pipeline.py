"""End-to-end pipeline orchestration.

    SRT → analysis → beat-plan → visual-plan → DSL → render-plan →
    entrance-plan → film/index.html → validation-report

Every stage writes its artifact to <out>/work/ before the next stage runs, so
a failure always leaves a complete audit trail (skill: 09-validation-repair).
"""
import os

import beat_planner
import composition_planner
import entrance_planner
import html_adapter
import srt_parser
import validator
import visual_director
from common import dump_json, ensure_dir

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(srt_path, out_dir, overrides_path=None, render_previews=True, log=print):
    work = ensure_dir(os.path.join(out_dir, "work"))
    preview = ensure_dir(os.path.join(out_dir, "preview"))
    film = ensure_dir(os.path.join(out_dir, "film"))
    ensure_dir(os.path.join(out_dir, "final"))

    log("→ SRT 解析与语义分析")
    analysis = srt_parser.analyze(srt_path)
    dump_json(analysis, os.path.join(work, "srt-analysis.json"))
    if analysis["errors"]:
        raise SystemExit("SRT 解析存在 ERROR: %s" % analysis["errors"])

    log("→ Beat 基线切分")
    beats = beat_planner.plan_beats(analysis["cues"])
    dump_json({"timing_source": "srt",
               "total_duration_sec": analysis["total_duration_sec"],
               "beats": beats}, os.path.join(work, "beat-plan.json"))
    log("  %d cues → %d beats" % (len(analysis["cues"]), len(beats)))

    log("→ 导演层（Visual Claim / 强调 / 信息编码 / 策略）")
    overrides = visual_director.load_overrides(overrides_path)
    visual_plan, dsl = visual_director.direct(beats, overrides)
    dump_json(visual_plan, os.path.join(work, "visual-plan.json"))
    dump_json(dsl, os.path.join(work, "visual-dsl.json"))

    log("→ 构图求解（Blueprint → Render Plan，一次算完）")
    render_plan, layout_intent, footprint, layout_audit = composition_planner.plan(dsl)
    dump_json(render_plan, os.path.join(work, "render-plan.json"))
    dump_json(layout_intent, os.path.join(work, "layout-intent.json"))
    dump_json(footprint, os.path.join(work, "content-footprint.json"))
    dump_json(layout_audit, os.path.join(work, "layout-audit.json"))

    log("→ 入场编排（cue 序列 / 节奏预算 / handoff）")
    entrance = entrance_planner.plan(dsl)
    ent_audit = entrance_planner.audit(entrance)
    if ent_audit["status"] != "PASS":
        dump_json(entrance, os.path.join(work, "entrance-plan.json"))
        raise SystemExit("入场编排门禁未通过: %s" % ent_audit["issues"])
    dump_json(entrance, os.path.join(work, "entrance-plan.json"))

    log("→ 编译 film/index.html（只读产物，禁止手改）")
    title = os.path.splitext(os.path.basename(srt_path))[0]
    html_adapter.compile(dsl, render_plan, entrance, title, film)

    log("→ 校验（schema / L1 / L3 光栅探针）")
    report = validator.validate(PROJECT_ROOT, work, preview, render=render_previews)
    log("  校验结果: %s" % report["status"])
    for i in report["issues"][:8]:
        log("  [%s] %s %s" % (i["layer"], i["code"], i["msg"]))
    return report
