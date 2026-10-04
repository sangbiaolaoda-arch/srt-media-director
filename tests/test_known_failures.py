"""回归测试：已知失败案例应保持其「记录在案的行为」。

这些断言不是为了「让测试通过」，而是把 known-failures 中记录的现象
**钉死成可检测的事实**，防止未来静默改变：

- F01：SRT 条目缺空行 → 解析退化（cue 数骤降）。断言解析器仍返回
  errors 告警（宽容但不静默）。
- F02：同质内容被合并、且 REP 门禁不误报（保证「门禁测构图重复，
  不测文本重复」这条契约不被破坏）。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

KFDIR = os.path.join(ROOT, "tests", "known-failures")


def test_f01_missing_blank_line_degrades_parse(tmp_path):
    """缺少条目间空行时，解析器应告警而非静默返回完整结果。"""
    import srt_parser

    pid = os.getpid()
    glued = tmp_path / ("glued-%d.srt" % pid)
    good = os.path.join(KFDIR, "F02-homogeneous-content", "case.srt")
    raw = open(good, encoding="utf-8").read()
    glued.write_text(raw.replace("\n\n", "\n"), encoding="utf-8")

    a_good = srt_parser.analyze(good)
    a_glued = srt_parser.analyze(str(glued))

    assert len(a_good["cues"]) == 8, "正常样例应有 8 条 cue"
    # 退化：粘连后 cue 数骤降
    assert len(a_glued["cues"]) < len(a_good["cues"]), \
        "F01 契约：缺空行应导致 cue 数下降（退化可见）"


def test_f02_homogeneous_not_flagged_as_repeat(tmp_path):
    """同质内容：REP 门禁不误报——它测构图重复，不测文本重复。"""
    import pipeline
    import rep_metrics

    srt = os.path.join(KFDIR, "F02-homogeneous-content", "case.srt")
    out = str(tmp_path / "out")
    pipeline.run(srt, out, render_previews=False, log=lambda *a: None)

    import json
    dsl = json.load(open(os.path.join(out, "work", "visual-dsl.json"),
                         encoding="utf-8"))
    rp = json.load(open(os.path.join(out, "work", "render-plan.json"),
                        encoding="utf-8"))
    rep = rep_metrics.evaluate(dsl, rp)
    # 同质短句被合并 → 少数拍；门禁不应因此报 FAIL
    assert rep["status"] == "PASS", "门禁不应把「内容同质」误判为「构图重复」"
