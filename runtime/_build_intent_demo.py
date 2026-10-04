"""intent 演示：证明 Agent 输出「视觉意图」而非「模板选择」。

对照用户给的两个例子：
  错误（模板选择器）→ intent_layer 拒斥
  正确（视觉意图）  → 校验通过 → composition_compiler 编译成合法画面 → 渲染
"""
import sys, io, json
sys.path.insert(0, "/mnt/work/srt-media-director/runtime")
import cairosvg
from PIL import Image
import ref_frame as R
import intent_layer as IL
import composition_compiler as CC

S = 1.6
CW, CH = int(R.CANVAS_W * S), int(R.CANVAS_H * S)
OUT = "/mnt/cos/artifacts"

# ---- 用户给的「错误」例子：模板选择器 ----
WRONG = {"strategy": "cause_effect", "template": "left_to_right_flow",
         "hero_x": 300, "hero_y": 400}

# ---- 用户给的「正确」例子：视觉意图 ----
RIGHT = {
    "beat_id": "b_attention_07",
    "visual_claim": "small_repeated_actions_accumulate_into_large_change",
    "grammar": ["accumulation", "trajectory", "threshold"],
    "focal_point": "trajectory",
    "relationship": [
        {"from": "small_actions", "relation": "accumulate_into", "to": "trajectory"},
        {"from": "trajectory", "relation": "crosses", "to": "threshold"},
    ],
    "density": 0.62, "silence": False, "motion_intent": "accumulate_then_reveal",
    "entities": ["small_actions", "trajectory", "threshold"],
}

# ---- 第二个意图：不同语法，证明编译器通用（contrast）----
CONTRAST = {
    "beat_id": "b_attention_12",
    "visual_claim": "phone_nearby_vs_phone_elsewhere",
    "grammar": ["contrast"],
    "focal_point": "far",
    "relationship": [{"from": "near", "relation": "contrast_with", "to": "far"}],
    "density": 0.45, "silence": False, "motion_intent": "contrast_then_focus",
    "entities": ["near", "far"],
}


def render(spec):
    canvas = Image.new("RGBA", (CW, CH), spec["bg"])
    for el in spec["elements"]:
        png = cairosvg.svg2png(bytestring=el["svg"].encode("utf-8"),
                               output_width=CW, output_height=CH)
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        x, y, w, h = [int(v * S) for v in el["box"]]
        x = max(0, x); y = max(0, y)
        w = min(w, CW - x); h = min(h, CH - y)
        if w <= 0 or h <= 0:
            continue
        crop = im.crop((x, y, x + w, y + h))
        canvas.paste(crop, (x, y), crop)
    return canvas.convert("RGB")


log = {}
# 1) 拒斥模板选择器
log["wrong_is_template_selector"] = IL.is_template_selector(WRONG)
log["wrong_leak_keys"] = IL.template_leak_keys(WRONG)
log["wrong_validate_issues"] = [i["code"] for i in IL.validate_intent(WRONG)]

# 2) 接受视觉意图
log["right_is_template_selector"] = IL.is_template_selector(RIGHT)
log["right_validate_issues"] = [i["code"] for i in IL.validate_intent(RIGHT)]
log["contrast_validate_issues"] = [i["code"] for i in IL.validate_intent(CONTRAST)]

# 3) 编译器：意图 → 几何
spec_a, meta_a = CC.compile_intent(RIGHT)
spec_b, meta_b = CC.compile_intent(CONTRAST)
log["A_realization"] = meta_a["realization"]
log["A_audit"] = meta_a["issues"]
log["A_accent"] = R.count_accent(spec_a)
log["B_realization"] = meta_b["realization"]
log["B_audit"] = meta_b["issues"]
log["B_accent"] = R.count_accent(spec_b)
print(json.dumps(log, ensure_ascii=False, indent=2))

# 4) 渲染 A/B 并排
imgA = render(spec_a)
imgB = render(spec_b)
gap = 16
sheet = Image.new("RGB", (2 * CW + 3 * gap, CH + 2 * gap), (250, 250, 248))
sheet.paste(imgA, (gap, gap))
sheet.paste(imgB, (2 * gap + CW, gap))
sheet.save(f"{OUT}/intent-to-composition.png", quality=92)
imgA.save(f"{OUT}/intent-A-accumulation-trajectory-threshold.png")
imgB.save(f"{OUT}/intent-B-contrast.png")
print("saved intent-to-composition.png", sheet.size)
