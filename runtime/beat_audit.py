"""Beat 拆分诊断（v6.1）：把分拍结果摊成人可读的对照文件，专治「断句不合理」。

用法：
    python runtime/beat_audit.py "examples/run/10月4日.srt" --out work/beat-audit-10月4日.md

产出：
- beat-audit.md   逐拍明细 + 相邻边界对照 + 自动标注「可疑边界」
- beat-audit.json 机器可读（每拍 cue 列表 / 边界 / 语义对）

设计目标：让「错在哪一拍、切在哪个字之间、为什么被切开」一眼可见，
而不是让用户对着成片猜。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beat_planner  # noqa: E402
import semantic_grouper  # noqa: E402
import srt_parser  # noqa: E402

# 左句若以这些词收尾，多半「话没说完」，不该在此处切
_DANGLING_END = (
    "但", "可", "可是", "然而", "却", "如果", "因为", "所以", "于是", "当",
    "被", "觉得", "认为", "是", "的", "之后", "之前", "时候", "在", "里",
    "把", "让", "跟", "和", "与", "比", "就是", "就要", "也要", "还要",
    "而且", "并且", "只是", "就是", "像", "向", "从", "对", "给",
)
# 右句若以这些词开头，多半是上一句的延续，不该另起一拍
_CONT_START = (
    "才会", "才能", "才", "就", "也", "还", "又", "而", "而且", "并且",
    "是可以", "是", "知道", "可以", "能", "要", "得", "被", "把", "跟",
    "然后", "于是", "所以", "因为", "因此",
)


def _beats_and_cons(cues):
    plan = beat_planner.plan_beats(cues)
    cons = semantic_grouper.grouping_constraints(cues)

    # 语义对：cue id -> 关系标签（从真实分拍结果回填，保证与产物一致）
    pair_at = {}
    for b in plan:
        for p in b.get("semantic_pairs", []):
            fc = p.get("from_cue", p.get("from"))
            tc = p.get("to_cue", p.get("to"))
            pair_at.setdefault(fc, []).append("%s→#%s" % (p["type"], tc))
            pair_at.setdefault(tc, []).append("%s←#%s" % (p["type"], fc))
    return plan, cons, pair_at


def build(cues):
    plan, cons, pair_at = _beats_and_cons(cues)
    keep = set(cons["keep_with_next"])
    prefer = set(cons["prefer_with_next"])

    records = []
    for b in plan:
        c0, c1 = b["cue_range"]
        seg = cues[c0 - 1:c1]
        records.append({
            "beat_id": b["beat_id"],
            "cue_range": [c0, c1],
            "start_sec": round(b["start_sec"], 3),
            "end_sec": round(b["end_sec"], 3),
            "duration_sec": round(b["duration_sec"], 3),
            "role": b.get("semantic_role", ""),
            "narration": b["narration"],
            "cues": [
                {"id": c["id"], "start": round(c["start"], 3),
                 "end": round(c["end"], 3),
                 "dur": round(c["end"] - c["start"], 3),
                 "text": c["text"], "pairs": pair_at.get(c["id"], [])}
                for c in seg
            ],
            "semantic_pairs": b.get("semantic_pairs", []),
        })

    boundaries = []
    for i in range(len(records) - 1):
        a, b = records[i], records[i + 1]
        lc = a["cues"][-1]
        rc = b["cues"][0]
        lpos = lc["id"] - 1        # keep/prefer 存的是 0 基下标
        left = lc["text"].rstrip("，。！？、；：,.!? ")
        flags = []
        for d in _DANGLING_END:
            if left.endswith(d):
                flags.append("左句以「%s」收尾（话没说完）" % d)
                break
        for s in _CONT_START:
            if rc["text"].startswith(s):
                flags.append("右句以「%s」起头（承接上一句）" % s)
                break
        if lpos in keep:
            flags.append("❌ 硬约束被违反：本应与下一句同拍却切开（bug）")
        elif lpos in prefer:
            flags.append("软约束建议同拍（prefer_with_next）")
        if rc["dur"] <= 1.0:
            flags.append("右句极短（%.2fs，孤立碎片）" % rc["dur"])
        boundaries.append({
            "between": "%s | %s" % (a["beat_id"], b["beat_id"]),
            "left_cue": lc["id"], "right_cue": rc["id"],
            "left_text": lc["text"], "right_text": rc["text"],
            "right_dur": rc["dur"],
            "protected_by_hard": lpos in keep,
            "flags": flags,
        })
    return records, boundaries, cons


def to_md(records, boundaries, cons, src):
    sus = [b for b in boundaries if b["flags"]]
    lines = []
    lines.append("# Beat 拆分对照（断句诊断）")
    lines.append("")
    lines.append("- 来源 SRT：`%s`" % src)
    lines.append("- 共 %d 拍 / %d 处边界" % (len(records), len(boundaries)))
    lines.append("- 硬约束 keep_with_next（不可切开）：%d 处" %
                 len(cons["keep_with_next"]))
    lines.append("- 软约束 prefer_with_next（尽量同拍）：%d 处" %
                 len(cons["prefer_with_next"]))
    lines.append("- **自动标记的可疑边界：%d 处**" % len(sus))
    lines.append("")

    lines.append("## 一、可疑边界（先看这里，逐条挑错）")
    lines.append("")
    if not sus:
        lines.append("（无自动命中的可疑边界）")
    for b in sus:
        lines.append("### ⚠️ %s" % b["between"])
        lines.append("")
        lines.append("- 左句 `#%02d`：%s  ✂️" % (b["left_cue"], b["left_text"]))
        lines.append("- 右句 `#%02d`：%s" % (b["right_cue"], b["right_text"]))
        for f in b["flags"]:
            lines.append("  - %s" % f)
        lines.append("")

    lines.append("## 二、全部边界对照")
    lines.append("")
    lines.append("| 边界 | 左拍末句 | 右拍首句 | 右句时长 | 硬约束 | 标记 |")
    lines.append("|---|---|---|---|---|---|")
    for b in boundaries:
        lines.append("| %s | %s | %s | %.2fs | %s | %s |" % (
            b["between"], b["left_text"], b["right_text"], b["right_dur"],
            "✅" if b["protected_by_hard"] else "—",
            "；".join(b["flags"]) if b["flags"] else "—"))
    lines.append("")

    lines.append("## 三、逐拍明细")
    lines.append("")
    for r in records:
        lines.append("### %s  ·  %.2f–%.2fs（%.2fs）·  %s" % (
            r["beat_id"], r["start_sec"], r["end_sec"], r["duration_sec"],
            r["role"]))
        lines.append("")
        lines.append("字幕 #%d–#%d：" % (r["cue_range"][0], r["cue_range"][1]))
        for c in r["cues"]:
            tag = ("  ←[%s]" % ",".join(c["pairs"])) if c["pairs"] else ""
            lines.append("- `#%02d` %.2f–%.2fs（%.2fs）  %s%s" % (
                c["id"], c["start"], c["end"], c["dur"], c["text"], tag))
        lines.append("")
        lines.append("> 拼接：%s" % r["narration"])
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--out", default="work/beat-audit.md")
    args = ap.parse_args()

    analysis = srt_parser.analyze(args.srt)
    cues = analysis["cues"]
    records, boundaries, cons = build(cues)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(to_md(records, boundaries, cons, args.srt))
    json_path = os.path.splitext(args.out)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"source": args.srt, "beats": records,
                   "boundaries": boundaries}, f, ensure_ascii=False, indent=2)

    sus = [b for b in boundaries if b["flags"]]
    print("cues=%d  beats=%d  boundaries=%d  suspicious=%d" % (
        len(cues), len(records), len(boundaries), len(sus)))
    print("hard_keep=%d  soft_prefer=%d" % (
        len(cons["keep_with_next"]), len(cons["prefer_with_next"])))
    print("→ %s" % args.out)
    print("→ %s" % json_path)


if __name__ == "__main__":
    main()
