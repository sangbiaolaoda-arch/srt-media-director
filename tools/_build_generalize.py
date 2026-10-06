"""泛化验证渲染：证明学到的是『构图规则』而非抄三张图。

上排 = 用规则复现参考帧（hero / chain / compare 系）
下排 = 用同一套规则外推出参考帧**没有**的构型（quadrants / timeline / stack）
两张并排图必须都成立，才能说明「复现 + 泛化」= 真学会。
"""
import os, sys, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime"))
import cairosvg
from PIL import Image
import ref_frame as R

S = 1.6
CW, CH = int(680 * S), int(382 * S)
OUT = "/mnt/cos/artifacts"


def strip_layer(svg, canvas_w, canvas_h):
    """把单元素透明图层合成到整幅画布，返回 PIL 图。"""
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                           output_width=canvas_w, output_height=canvas_h,
                           background_color=None)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def render(spec):
    """按图层渲染一帧最终态（所有元素在各自框内贴到位）。"""
    canvas = Image.new("RGBA", (CW, CH), spec["bg"])
    layer = strip_layer(('''<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="764" '''
                          '''viewBox="0 0 680 382">%s</svg>'''), CW, CH)
    # 逐个元素：把元素 svg 渲染为整幅，再裁剪到其 box 区域贴回（保持精确位置）
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


# ---- 上排：复现参考帧 ----
reproduce = [
    R.frame_hero("为什么你总在分心？", "不是意志力差，是注意力被反复打断",
                 R.icon_phone(500, 200, 0.92, badge=3), (440, 80, 136, 236)),
    R.frame_chain("一次通知，三步代价", [
        ("通知响起", R.icon_bell(0, 0, 1.0), False),
        ("专注被打断", R.icon_focus_break(0, 0, 1.0), True),
        ("回到状态要时间", R.icon_bar_half(0, 0, 1.0), False)],
        caption="每次切换，都要重新找回刚才的思路"),
    R.frame_compare(
        "离手机远一点，更能专注",
        {"label": "手机在手边", "bar": 54, "bar_accent": False,
         "icon_inner": R.icon_phone(246, 238, 0.24), "icon_box": (226, 206, 44, 68)},
        {"label": "手机在另一个房间", "bar": 130, "bar_accent": True,
         "icon_inner": R.icon_door(562, 245, 1.0), "icon_box": (534, 208, 60, 76)},
        caption="示意图：柱高仅表示相对趋势，不代表具体数值"),
]

# ---- 下排：参考帧没有的新构型（同规则外推）----
generalize = [
    R.frame_quadrants("分心的四种代价", [
        ("通知", lambda cx, cy: R.icon_bell(cx, cy, 0.72), False),
        ("打断", lambda cx, cy: R.icon_focus_break(cx, cy, 0.78), False),
        ("等待", lambda cx, cy: R.icon_bar_half(cx, cy, 0.78), False),
        ("回不去", lambda cx, cy: R.icon_door(cx, cy, 0.9), True)],
        caption="四象限：同一强调纪律，规则自动分槽"),
    R.frame_timeline("一次通知的时间线", [
        ("响", "", False), ("看", "", False), ("断", "", True), ("续", "", False)],
        caption="时间轴：等距分点，规则外推（参考帧无）"),
    R.frame_stack("把注意力抢回来", [
        ("关掉通知", lambda cx, cy: R.icon_bell(cx, cy, 0.5), True),
        ("把手机放远", lambda cx, cy: R.icon_door(cx, cy, 0.6), False),
        ("重新找回思路", lambda cx, cy: R.icon_focus_break(cx, cy, 0.7), False)],
        caption="纵向清单：rows(n) 规则外推（参考帧无）"),
]

row1 = [render(s) for s in reproduce]
row2 = [render(s) for s in generalize]

gap = 12
tw = row1[0].width
sheet = Image.new("RGB", (3 * tw + 4 * gap, 2 * row1[0].height + 3 * gap), (250, 250, 248))
for i, im in enumerate(row1):
    sheet.paste(im, (gap + i * (tw + gap), gap))
for i, im in enumerate(row2):
    sheet.paste(im, (gap + i * (tw + gap), 2 * gap + row1[0].height))
sheet.save(os.path.join(OUT, "ref-rule-generalize.png"), quality=92)
print("saved ref-rule-generalize.png", sheet.size)

# 单帧也存一份，便于单看
for i, im in enumerate(row2):
    im.save(os.path.join(OUT, f"new-composition-{i+1}.png"))
print("done")
