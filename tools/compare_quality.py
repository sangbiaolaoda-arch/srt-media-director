#!/usr/bin/env python3
"""Version comparison — baseline vs candidate, from machine metrics (M3 P1).

Never answers "does it feel better?".  It answers, per case and per metric:
which cases improved, which regressed, which metrics moved, whether anything got
better locally but worse overall, and whether an effect is confined to a single
content category.

Inputs are two ``quality-eval-report.json`` files (see real_srt_quality_eval.py).
Output layout::

    comparison/
    ├── machine-diff.json
    ├── score-diff.json          (L4 dimension deltas; PENDING-aware)
    ├── contact-sheet-before.png
    ├── contact-sheet-after.png
    └── summary.md

Usage:
    python tools/compare_quality.py --baseline DIR_OR_JSON --candidate DIR_OR_JSON --out DIR
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "runtime"))

from PIL import Image  # noqa: E402

DIMENSIONS = ["semantic_expression", "composition", "hierarchy", "motion",
              "continuity", "visual_richness", "repetition", "ppt_feeling", "overall"]
# metrics where an INCREASE is better; everything else is treated as lower-better
HIGHER_BETTER = {"distinct_strategies", "ink_mean", "colors_mean", "elements", "beats"}
# anti-ppt signals where lower is better
LOWER_BETTER = {"text_ratio", "text_dominant_beats", "template_repeat",
                "max_consecutive_same_strategy", "decoration_ratio",
                "fade_only_motion_ratio", "static_beat_ratio", "encoding_repeat"}


def _load(path):
    if os.path.isdir(path):
        path = os.path.join(path, "quality-eval-report.json")
    return json.load(open(path, encoding="utf-8"))


def _flat_metrics(case):
    m = dict(case.get("machine_metrics", {}))
    ap = m.pop("anti_ppt", {}) or {}
    m.pop("strategy_histogram", None)
    for k, v in ap.items():
        if not k.startswith("_"):
            m["anti_ppt." + k] = v
    return m


def _norm_case_key(srt):
    return os.path.basename(srt)


def _grid(sheet_paths, out_path, cols=4, tw=320, th=180, gap=10):
    items = []
    for label, p in sheet_paths:
        if os.path.isfile(p):
            items.append((label, Image.open(p).convert("RGB")))
    if not items:
        return None
    rows = (len(items) + cols - 1) // cols
    grid = Image.new("RGB", (cols * tw + (cols + 1) * gap,
                             rows * th + (rows + 1) * gap), (248, 248, 245))
    for i, (_lbl, im) in enumerate(items):
        r, c = divmod(i, cols)
        grid.paste(im.resize((tw, th), Image.LANCZOS),
                   (gap + c * (tw + gap), gap + r * (th + gap)))
    grid.save(out_path, quality=90)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label-before", default="baseline")
    ap.add_argument("--label-after", default="candidate")
    args = ap.parse_args()

    base = _load(args.baseline)
    cand = _load(args.candidate)
    os.makedirs(args.out, exist_ok=True)

    bcases = {_norm_case_key(c["srt"]): c for c in base["cases"]}
    ccases = {_norm_case_key(c["srt"]): c for c in cand["cases"]}
    keys = sorted(set(bcases) | set(ccases))

    per_case = []
    better = worse = same = 0
    # aggregate metric directions
    moved = {}
    comparable = {}  # metric -> #cases where the metric is present in BOTH versions
    for k in keys:
        b, c = bcases.get(k), ccases.get(k)
        if not b or not c:
            per_case.append({"case": k, "status": "only-in-one-version"})
            continue
        bm, cm = _flat_metrics(b), _flat_metrics(c)
        deltas = {}
        for metric in sorted(set(bm) | set(cm)):
            bv, cv = bm.get(metric), cm.get(metric)
            if isinstance(bv, (int, float)) and isinstance(cv, (int, float)):
                # mean delta denominator = #comparable cases (metric present in both),
                # NOT only the cases where it happened to change.
                comparable[metric] = comparable.get(metric, 0) + 1
                if bv != cv:
                    deltas[metric] = round(cv - bv, 4)
                    moved.setdefault(metric, []).append(cv - bv)
        # overall direction: count improved vs regressed metrics
        imp = reg = 0
        for metric, d in deltas.items():
            if metric in HIGHER_BETTER:
                imp += d > 0
                reg += d < 0
            elif metric in LOWER_BETTER:
                imp += d < 0
                reg += d > 0
        verdict = "improved" if imp > reg else "regressed" if reg > imp else "unchanged"
        better += verdict == "improved"
        worse += verdict == "regressed"
        same += verdict == "unchanged"
        per_case.append({"case": k, "category": c.get("category"),
                         "verdict": verdict, "improved_metrics": imp,
                         "regressed_metrics": reg, "metric_deltas": deltas,
                         "baseline_status": b.get("production_path", {}).get("status"),
                         "candidate_status": c.get("production_path", {}).get("status")})

    # score diff (L4 dimensions; may be PENDING in both -> not comparable)
    score_diff = []
    for k in keys:
        b, c = bcases.get(k), ccases.get(k)
        if not b or not c:
            continue
        row = {"case": k}
        for d in DIMENSIONS:
            bv = (b.get("scores") or {}).get(d)
            cv = (c.get("scores") or {}).get(d)
            row[d] = {"baseline": bv, "candidate": cv,
                      "comparable": isinstance(bv, (int, float)) and isinstance(cv, (int, float)),
                      "delta": (round(cv - bv, 3)
                                if isinstance(bv, (int, float)) and isinstance(cv, (int, float)) else None)}
        score_diff.append(row)

    # category confinement: is an improvement confined to one category?
    cats = {}
    for pc in per_case:
        if pc.get("verdict"):
            cats.setdefault(pc.get("category"), {"improved": 0, "regressed": 0, "unchanged": 0})
            cats[pc["category"]][pc["verdict"]] += 1

    machine_diff = {
        "label_before": args.label_before,
        "label_after": args.label_after,
        "summary_counts": {"improved": better, "regressed": worse, "unchanged": same},
        "metric_deltas_mean": {m: round(sum(v) / comparable.get(m, len(v)), 4) for m, v in moved.items()},
        "category_breakdown": cats,
        "per_case": per_case,
        "notes": [
            "improved/regressed = count of metrics that moved in the better/worse direction",
            "metric_deltas_mean = sum(case delta) / (#cases where the metric is comparable), so unchanged/non-comparable cases count as 0",
            "HIGHER_BETTER=%s" % sorted(HIGHER_BETTER),
            "LOWER_BETTER(anti-ppt)=%s" % sorted(LOWER_BETTER),
        ],
    }
    json.dump(machine_diff, open(os.path.join(args.out, "machine-diff.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"dimensions": DIMENSIONS, "cases": score_diff},
              open(os.path.join(args.out, "score-diff.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # contact-sheet before/after grids
    def _sheets(report):
        root = os.path.dirname(os.path.abspath(
            os.path.join(args.baseline if report is base else args.candidate,
                         "quality-eval-report.json")))
        out = []
        for c in report["cases"]:
            cs = (c.get("render") or {}).get("contact_sheet")
            if cs:
                out.append((_norm_case_key(c["srt"]), os.path.join(root, cs)))
        return out

    _grid(_sheets(base), os.path.join(args.out, "contact-sheet-before.png"))
    _grid(_sheets(cand), os.path.join(args.out, "contact-sheet-after.png"))

    # summary.md
    local_better_overall_worse = any(
        pc.get("verdict") == "improved" and better and sum(
            1 for x in per_case if x.get("verdict") == "regressed") > better
        for pc in per_case)
    lines = ["# Quality comparison: %s -> %s" % (args.label_before, args.label_after), ""]
    lines.append("## Headline")
    lines.append("- cases improved: **%d**, regressed: **%d**, unchanged: **%d**" % (better, worse, same))
    lines.append("- local-better/overall-worse: **%s**" % ("YES" if local_better_overall_worse else "no"))
    lines.append("- effect confined to one category: **%s**" % (
        "yes" if (len([c for c in cats if cats[c]["improved"]]) == 1 and better) else "no"))
    lines.append("")
    lines.append("## Mean metric deltas")
    for m, v in sorted(machine_diff["metric_deltas_mean"].items(), key=lambda x: -abs(x[1])):
        lines.append("- `%s`: %+g" % (m, v))
    lines.append("")
    lines.append("## Per-case verdicts")
    for pc in per_case:
        if pc.get("verdict"):
            lines.append("- %-42s %-10s (+%d/-%d)" % (
                pc["case"], pc["verdict"], pc["improved_metrics"], pc["regressed_metrics"]))
    lines.append("")
    lines.append("> score-diff dimensions stay non-comparable until L4 scores stop being PENDING.")
    open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("wrote comparison to %s (improved=%d regressed=%d unchanged=%d)"
          % (args.out, better, worse, same))


if __name__ == "__main__":
    main()
