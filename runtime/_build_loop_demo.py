"""闭环产出证据：director_loop 跑多个意图 → 收集真实截图 → 拼联系表。

证明「Agent → VisualIntent → Compiler → RenderPlan → HTML/SVG → 截图 → Critic」
这条闭环真的产出光栅，而不是纸面描述。
"""
import sys, os, tempfile, json
sys.path.insert(0, "/mnt/work/srt-media-director/runtime")
from PIL import Image
import director_loop as DL

OUT = "/mnt/cos/artifacts"

intents = [
    {"beat_id": "accum", "visual_claim": "small_actions_accumulate_into_change",
     "grammar": ["accumulation", "trajectory", "threshold"], "focal_point": "trajectory",
     "relationship": [{"from": "small_actions", "relation": "accumulate_into", "to": "trajectory"},
                      {"from": "trajectory", "relation": "crosses", "to": "threshold"}],
     "density": 0.62, "silence": False, "motion_intent": "accumulate_then_reveal",
     "entities": ["small_actions", "trajectory", "threshold"]},
    {"beat_id": "contrast", "visual_claim": "near_vs_far",
     "grammar": ["contrast"], "focal_point": "far",
     "relationship": [{"from": "near", "relation": "contrast_with", "to": "far"}],
     "density": 0.45, "silence": False, "motion_intent": "contrast_then_focus",
     "entities": ["near", "far"]},
    {"beat_id": "cause", "visual_claim": "one_notification_three_costs",
     "grammar": ["causality", "progression"], "focal_point": "interrupt",
     "relationship": [{"from": "notify", "relation": "causes", "to": "interrupt"},
                      {"from": "interrupt", "relation": "precedes", "to": "recover"}],
     "density": 0.55, "silence": False, "motion_intent": "morph",
     "entities": ["notify", "interrupt", "recover"]},
]

d = tempfile.mkdtemp(prefix="loopout_")
summary = DL.run_intents(intents, d, max_repair=2)
print("closed-loop:", summary["passed"], "/", summary["total"], "PASS")

imgs = []
for r in summary["results"]:
    print(" ", r["beat_id"], r["verdict"], "backend=", r["backend"], "attempts=", r["attempts"])
    if r["png"] and os.path.exists(r["png"]):
        imgs.append((r["beat_id"], Image.open(r["png"]).convert("RGB")))

if imgs:
    w = max(im.width for _, im in imgs)
    gap = 14
    H = sum(im.height for _, im in imgs) + gap * (len(imgs) + 1)
    sheet = Image.new("RGB", (w + 2 * gap, H), (250, 250, 248))
    y = gap
    for _, im in imgs:
        sheet.paste(im, (gap, y))
        y += im.height + gap
    sheet.save(f"{OUT}/closed-loop-output.png", quality=92)
    print("saved closed-loop-output.png", sheet.size)
