"""P0 Real Content Evaluation harness.

For every real SRT in the repo: run the full production layers (srt_parser ->
beat_planner -> visual_director -> composition_planner -> entrance_planner),
collect machine metrics, render one settle frame per beat, and compose a
per-SRT contact sheet. Writes a dataset JSON + PNG contact sheets.

No ffmpeg required: frames come straight from raster_renderer.draw_frame.
"""
import json
import os
import sys

ROOT = "/mnt/work/smd"
OUT = "/mnt/cos/artifacts/p0-real-content-eval"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from PIL import Image, ImageDraw  # noqa: E402

import beat_planner  # noqa: E402
import composition_planner  # noqa: E402
import entrance_planner  # noqa: E402
import raster_renderer  # noqa: E402
import srt_parser  # noqa: E402
import visual_director  # noqa: E402
import jsonschema  # noqa: E402

ENTER_OK = {"fade", "rise", "pop", "inherit"}
EXIT_OK = {"fade", "sink", "shrink"}

SRTS = [
    ("examples/minimal/attention.srt", None),
    ("examples/run/attention-30s.srt", None),
    ("examples/run/10月2日.srt", None),
    ("examples/run/10月4日.srt", None),
    ("examples/showcase/01-explanatory-tech/case.srt", None),
    ("examples/showcase/02-narrative-emotion/case.srt", None),
    ("examples/showcase/03-data-comparison/case.srt", None),
    ("examples/showcase/04-longform-3min/case.srt", None),
    ("tests/golden/01-minimal/case.srt", None),
    ("tests/golden/02-numeric/case.srt", None),
    ("tests/known-failures/F02-homogeneous-content/case.srt", None),
]


def contact_sheet(items, out_path, cols=3, tw=426, th=240, gap=12):
    if not items:
        return None, None
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
    return out_path, sheet.size


dataset = {"cases": [], "summary": {}}
schema = json.load(open(os.path.join(ROOT, "schemas", "entrance-plan.schema.json")))

for srt, ov in SRTS:
    p = os.path.join(ROOT, srt)
    case = {"srt": srt, "exists": os.path.isfile(p)}
    if not case["exists"]:
        dataset["cases"].append(case)
        continue
    try:
        analysis = srt_parser.analyze(p)
        beats = beat_planner.plan_beats(analysis["cues"])
        _, dsl = visual_director.direct(beats, {})
        render_plan, _, _, layout_audit = composition_planner.plan(dsl)
        entrance = entrance_planner.plan(dsl)
        ent_audit = entrance_planner.audit(entrance)
        schema_ok = True
        try:
            jsonschema.validate(entrance, schema)
        except Exception:
            schema_ok = False
        toks, bad = set(), 0
        for b in entrance["beats"]:
            for lc in b["lifecycle"].values():
                toks.add("e:" + lc["enter"]["motion"])
                if lc["enter"]["motion"] not in ENTER_OK:
                    bad += 1
                if lc["exit"]:
                    toks.add("x:" + lc["exit"]["motion"])
                    if lc["exit"]["motion"] not in EXIT_OK:
                        bad += 1
        prev = None
        items, inks = [], []
        for beat in dsl["beats"]:
            pb = next(x for x in render_plan["beats"] if x["beat_id"] == beat["beat_id"])
            pe = next(x for x in entrance["beats"] if x["beat_id"] == beat["beat_id"])
            dur = max(beat["end_sec"] - beat["start_sec"], 0.01)
            t = beat["start_sec"] + min(0.80 * dur, max(dur - 0.05, 0.0))
            img = raster_renderer.draw_frame(beat, pb, pe, t, prev=prev)
            ratio, colors = raster_renderer.ink_stats(img)
            inks.append({"beat": beat["beat_id"], "ink_ratio": round(ratio, 4),
                         "distinct_colors": colors})
            items.append((beat["beat_id"], img))
            prev = (beat, pb, pe)
        name = srt.replace("/", "__").replace(".srt", "")
        cs_path = os.path.join(OUT, "contact-%s.png" % name)
        _, size = contact_sheet(items, cs_path)
        case.update({
            "cues": len(analysis["cues"]), "beats": len(beats),
            "layout_audit": layout_audit["status"],
            "entrance_audit": ent_audit["status"],
            "entrance_schema_valid": schema_ok,
            "illegal_motion_tokens": bad,
            "motion_tokens": sorted(toks),
            "ink": inks,
            "ink_mean": round(sum(i["ink_ratio"] for i in inks) / len(inks), 4),
            "colors_mean": round(sum(i["distinct_colors"] for i in inks) / len(inks), 1),
            "contact_sheet": os.path.basename(cs_path),
            "contact_size": size,
        })
        print("%-52s beats=%-2d layout=%s entrance=%s schema=%s illegal=%d"
              % (srt, len(beats), layout_audit["status"], ent_audit["status"], schema_ok, bad))
    except SystemExit as e:
        case["gate_fail"] = str(e)[:120]
        print("%-52s GATE_FAIL %s" % (srt, str(e)[:80]))
    except Exception as e:  # noqa: BLE001
        case["error"] = "%s: %s" % (type(e).__name__, str(e)[:120])
        print("%-52s ERROR %s" % (srt, str(e)[:80]))
    dataset["cases"].append(case)

ok = [c for c in dataset["cases"] if c.get("entrance_schema_valid") and not c.get("illegal_motion_tokens")]
dataset["summary"] = {
    "cases": len(dataset["cases"]),
    "entrance_schema_valid_and_legal": len(ok),
    "all_entrance_pass": all(c.get("entrance_audit") == "PASS" for c in dataset["cases"] if "entrance_audit" in c),
    "note": "F02-homogeneous-content is a documented known-failure case.",
}
json.dump(dataset, open(os.path.join(OUT, "real-content-eval.json"), "w"),
          ensure_ascii=False, indent=2)
print("SUMMARY:", json.dumps(dataset["summary"], ensure_ascii=False))
