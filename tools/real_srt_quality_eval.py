#!/usr/bin/env python3
"""Real SRT Quality Evaluation harness (P0-3).

Distinct from the regression dataset (tools/real_content_eval.py): that file
proves "the code did not break" (legacy==canonical).  THIS file produces the
per-case material a human/agent needs to judge "is the film actually good?".

For every fixed corpus SRT it runs the FULL production path (pipeline.run),
records machine metrics (objective, automatic) and the render/contact-sheet
pointers, and writes a 9-dimension evaluation record whose scores ALL start
PENDING.  It never fills a score by itself: L4 quality is human/agent work and a
gate forbids machine-faked scores.

Dimensions: semantic_expression, composition, hierarchy, motion, continuity,
visual_richness, repetition, ppt_feeling, overall.

Usage:
    python tools/real_srt_quality_eval.py [--out DIR] [--limit N] [--category C]
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(REPO, "runtime")
sys.path.insert(0, RUNTIME)

from PIL import Image, ImageDraw  # noqa: E402

CORPUS_ROOT = os.path.join(REPO, "tests", "corpus", "real-content")
DIMENSIONS = ["semantic_expression", "composition", "hierarchy", "motion",
              "continuity", "visual_richness", "repetition", "ppt_feeling", "overall"]
SCHEMA_VERSION = "quality-eval-report.v1"
DEFAULT_OUT = os.path.join(REPO, "docs", "real-srt-quality-eval")


def _srt_list(category=None):
    out = []
    for root, _dirs, files in os.walk(CORPUS_ROOT):
        for f in sorted(files):
            if f.endswith(".srt"):
                p = os.path.join(root, f)
                cat = os.path.relpath(root, CORPUS_ROOT).split(os.sep)[0]
                if category and cat != category:
                    continue
                out.append((p, cat))
    return sorted(out)


def _contact_sheet(items, out_path, cols=3, tw=426, th=240, gap=12):
    if not items:
        return None
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap,
                              rows * th + (rows + 1) * gap), (250, 250, 248))
    dr = ImageDraw.Draw(sheet)
    for idx, (label, im) in enumerate(items):
        r, c = divmod(idx, cols)
        x = gap + c * (tw + gap)
        y = gap + r * (th + gap)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        dr.rectangle([x - 1, y - 1, x + tw, y + th], outline=(200, 200, 195))
        dr.text((x + 6, y + 6), label, fill=(30, 30, 30))
    sheet.save(out_path, quality=92)
    return os.path.getsize(out_path)


def _machine_metrics(work, dsl, entrance, report):
    import raster_renderer
    rp = json.load(open(os.path.join(work, "render-plan.json"), encoding="utf-8"))
    inks = []
    for beat in dsl["beats"]:
        pb = next(x for x in rp["beats"] if x["beat_id"] == beat["beat_id"])
        pe = next(x for x in entrance["beats"] if x["beat_id"] == beat["beat_id"])
        dur = max(beat["end_sec"] - beat["start_sec"], 0.01)
        t = beat["start_sec"] + min(0.80 * dur, max(dur - 0.05, 0.0))
        img = raster_renderer.draw_frame(beat, pb, pe, t)
        ratio, colors = raster_renderer.ink_stats(img)
        inks.append((ratio, colors))
    strategies = {}
    for b in dsl["beats"]:
        strategies[b.get("strategy")] = strategies.get(b.get("strategy"), 0) + 1
    return {
        "cues": None,
        "beats": len(dsl["beats"]),
        "elements": sum(len(b.get("elements", [])) for b in dsl["beats"]),
        "distinct_strategies": len(strategies),
        "strategy_histogram": strategies,
        "ink_mean": round(sum(i[0] for i in inks) / len(inks), 4) if inks else 0.0,
        "colors_mean": round(sum(i[1] for i in inks) / len(inks), 1) if inks else 0.0,
        "validator_status": report.get("status"),
        "l4": report.get("layers", {}).get("l4"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--category", default=None)
    args = ap.parse_args()

    import pipeline

    from verification import defaults  # noqa: F401  (parity)

    os.makedirs(args.out, exist_ok=True)
    srts = _srt_list(args.category)
    if args.limit:
        srts = srts[:args.limit]

    category_counts = {}
    cases = []
    for srt_path, cat in srts:
        rel = os.path.relpath(srt_path, REPO)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        out_dir = os.path.join(args.out, "runs", rel.replace(os.sep, "__"))
        case = {"srt": rel, "category": cat, "production_path": {}, "render": {},
                "machine_metrics": {}, "scores": {}, "verdict": "PENDING", "notes": ""}
        try:
            report = pipeline.run(srt_path, out_dir, render_previews=True, log=lambda *a: None)
            work = os.path.join(out_dir, "work")
            dsl = json.load(open(os.path.join(work, "visual-dsl.json"), encoding="utf-8"))
            entrance = json.load(open(os.path.join(work, "entrance-plan.json"), encoding="utf-8"))
            film_index = os.path.join(out_dir, "film", "index.html")
            receipt = json.load(open(os.path.join(work, "run-receipt.json"), encoding="utf-8"))
            case["production_path"] = {
                "status": report.get("status"),
                "stages": [s["stage"] for s in receipt["stages"]],
                "next_stage": receipt["next_stage"],
                "verdict": receipt["verdict"]["verdict"],
                "work_dir": os.path.relpath(work, REPO),
            }
            case["machine_metrics"] = _machine_metrics(work, dsl, entrance, report)
            # render one frame per beat into a contact sheet
            import raster_renderer
            rp = json.load(open(os.path.join(work, "render-plan.json"), encoding="utf-8"))
            items = []
            for beat in dsl["beats"]:
                pb = next(x for x in rp["beats"] if x["beat_id"] == beat["beat_id"])
                pe = next(x for x in entrance["beats"] if x["beat_id"] == beat["beat_id"])
                dur = max(beat["end_sec"] - beat["start_sec"], 0.01)
                t = beat["start_sec"] + min(0.80 * dur, max(dur - 0.05, 0.0))
                items.append((beat["beat_id"], raster_renderer.draw_frame(beat, pb, pe, t)))
            sheet_name = "contact-%s.png" % rel.replace(os.sep, "__").replace(".srt", "")
            sheet_path = os.path.join(args.out, sheet_name)
            size = _contact_sheet(items, sheet_path)
            case["render"] = {"contact_sheet": sheet_name, "bytes": size,
                              "film_index": os.path.relpath(film_index, REPO),
                              "film_exists": os.path.exists(film_index)}
            for dim in DIMENSIONS:
                case["scores"][dim] = "PENDING"
            print("%-58s beats=%-2d strat=%-2d ink=%.3f ok" %
                  (rel, case["machine_metrics"]["beats"],
                   case["machine_metrics"]["distinct_strategies"],
                   case["machine_metrics"]["ink_mean"]))
        except SystemExit as e:
            case["production_path"] = {"status": "GATE_FAIL", "detail": str(e)[:160]}
            print("%-58s GATE_FAIL %s" % (rel, str(e)[:70]))
        except Exception as e:  # noqa: BLE001
            case["production_path"] = {"status": "ERROR", "detail": "%s: %s" % (type(e).__name__, str(e)[:140])}
            print("%-58s ERROR %s" % (rel, str(e)[:70]))
        cases.append(case)

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_from": "tools/real_srt_quality_eval.py",
        "metrics_pending": True,
        "dimensions": DIMENSIONS,
        "corpus": {"root": os.path.relpath(CORPUS_ROOT, REPO),
                   "count": len(cases), "categories": category_counts},
        "cases": cases,
    }

    # validate against schema (the no-fake contract)
    schema_path = os.path.join(REPO, "schemas", "quality-eval-report.schema.json")
    if os.path.isfile(schema_path):
        import jsonschema
        jsonschema.validate(report, json.load(open(schema_path, encoding="utf-8")))

    out_json = os.path.join(args.out, "quality-eval-report.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("wrote %s (%d cases, all PENDING)" % (os.path.relpath(out_json, REPO), len(cases)))


if __name__ == "__main__":
    main()
