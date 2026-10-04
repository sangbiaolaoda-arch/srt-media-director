"""逐元素入场动画渲染：用 ref_frame 的图层规范，对每个元素做独立入场。"""
import os, sys, io, subprocess, shutil
sys.path.insert(0, "/mnt/work/srt-media-director/runtime")
import cairosvg
from PIL import Image
import imageio_ffmpeg
import ref_frame as R

S = 2.0
CW, CH = int(680 * S), int(382 * S)   # 1360x764 (viewBox 精确 2x)
FPS = 15
OUT = "/mnt/work/refanim"
BG = R.BG
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)


def load(svg):
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=CW, output_height=CH)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def ease(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def with_alpha(im, p):
    a = im.getchannel("A").point(lambda v: int(v * p))
    im.putalpha(a); return im


# ---- 7 拍内容（注意力/分心，与参考帧同源）+ 每拍时长 ----
beats = []
beats.append((4.0, R.frame_hero("为什么你总在分心？", "不是意志力差，是注意力被反复打断",
                                R.icon_phone(500, 200, 0.92, badge=3), (440, 80, 136, 236))))
beats.append((3.5, R.frame_statement([("不是意志力差", False), ("是注意力被反复打断", True)], size=30)))
beats.append((4.5, R.frame_chain("一次通知，要付出三步代价", [
    ("通知响起", R.icon_bell(123, 190, 1.0), False),
    ("专注被打断", R.icon_focus_break(340, 186, 1.0), False),
    ("回到状态要时间", R.icon_bar_half(557, 189, 1.0), False)])))
beats.append((4.5, R.frame_chain("一次通知，三步代价", [
    ("通知响起", R.icon_bell(123, 190, 1.0), False),
    ("专注被打断", R.icon_focus_break(340, 186, 1.0), True),
    ("回到状态要时间", R.icon_bar_half(557, 189, 1.0), False)],
    caption="每次切换，都要重新找回刚才的思路")))
beats.append((4.0, R.frame_bar_detail("回到状态要时间", 0.55,
                                      caption="重新进入专注不是瞬间完成的", label="恢复进度")))
beats.append((4.5, R.frame_compare(
    "离手机远一点，更能专注",
    {"label": "手机在手边", "bar": 54, "bar_accent": False,
     "icon_inner": R.icon_phone(246, 238, 0.24, col=R.INK), "icon_box": (226, 206, 44, 68)},
    {"label": "手机在另一个房间", "bar": 130, "bar_accent": True,
     "icon_inner": R.icon_door(562, 245, 1.0), "icon_box": (534, 208, 60, 76)},
    caption="示意图：柱高仅表示相对趋势，不代表具体数值")))
beats.append((4.5, R.frame_hero("离手机远一点，更能专注", "把注意力还给当下要做的事",
                                R.icon_phone(500, 200, 0.92, badge=None), (440, 80, 136, 236))))

# 预渲染每个元素图层
beats_layers = []
for dur, spec in beats:
    layers = []
    for i, el in enumerate(spec["elements"]):
        at = el["at"] if el["at"] is not None else i * 0.18
        box = tuple(int(v * S) for v in el["box"])
        layers.append((load(el["svg"]), box, el["motion"], at))
    beats_layers.append((dur, layers))

# 逐帧渲染（每元素独立入场）
starts = []
idx = 0
for dur, layers in beats_layers:
    starts.append(idx)
    nf = max(1, int(round(dur * FPS)))
    for k in range(nf):
        t = k / FPS
        canvas = Image.new("RGBA", (CW, CH), BG)
        for layer, (x, y, w, h), motion, at in layers:
            p = ease((t - at) / 0.5)
            if p <= 0:
                continue
            crop = layer.crop((x, y, x + w, y + h))
            if motion == "fade":
                canvas.paste(with_alpha(crop, p), (x, y), crop)
            elif motion == "rise":
                dy = int((1 - p) * 26 * S)
                canvas.paste(with_alpha(crop, p), (x, y + dy), crop)
            elif motion == "pop":
                kk = 0.6 + 0.4 * p
                nw, nh = max(1, int(w * kk)), max(1, int(h * kk))
                cc = with_alpha(crop.resize((nw, nh)), p)
                canvas.paste(cc, (int(x + (w - nw) / 2), int(y + (h - nh) / 2)), cc)
            elif motion == "draw":
                cw = max(1, int(w * p))
                cc = crop.crop((0, 0, cw, h)); canvas.paste(cc, (x, y), cc)
            elif motion == "grow":
                hh = max(1, int(h * p))
                cc = crop.crop((0, h - hh, w, h)); canvas.paste(cc, (x, y + h - hh), cc)
        canvas.convert("RGB").save(f"{OUT}/f_{idx:04d}.png")
        idx += 1
print("frames:", idx, "beat starts:", starts)

# 编码
ff = imageio_ffmpeg.get_ffmpeg_exe()
mp4 = "/mnt/work/refanim-30s.mp4"
subprocess.run([ff, "-y", "-framerate", str(FPS), "-i", f"{OUT}/f_%04d.png",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
shutil.copyfile(mp4, "/mnt/cos/artifacts/refanim-30s.mp4")
print("mp4 bytes:", os.path.getsize(mp4))

# 联系表：每拍末帧
reps = []
for bi, (dur, layers) in enumerate(beats_layers):
    nf = max(1, int(round(dur * FPS)))
    reps.append(Image.open(f"{OUT}/f_{starts[bi]+nf-2:04d}.png").convert("RGB"))
tw = 560; gap = 10; cols = 3
sc = [im.resize((tw, int(im.height * tw / im.width))) for im in reps]
cw, ch = sc[0].size
rows = (len(sc) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cw + (cols + 1) * gap, rows * ch + (rows + 1) * gap), (255, 255, 255))
for i, im in enumerate(sc):
    r, c = divmod(i, cols); sheet.paste(im, (gap + c * (cw + gap), gap + r * (ch + gap)))
sheet.save("/mnt/cos/artifacts/refanim-30s-联系表.jpg", quality=90)

# 入场胶片条（compare 拍 = index 5）：看元素是否逐个进场
compare_start = starts[5]
ts = [0.02, 0.20, 0.42, 0.62, 0.90, 1.60]
strip = [Image.open(f"{OUT}/f_{compare_start+int(t*FPS):04d}.png").convert("RGB") for t in ts]
w = 620; s2 = [im.resize((w, int(im.height * w / im.width))) for im in strip]
st = Image.new("RGB", (len(s2) * (w + 8) + 8, s2[0].height + 16), (235, 235, 233))
for i, im in enumerate(s2):
    st.paste(im, (8 + i * (w + 8), 8))
st.save("/mnt/cos/artifacts/refanim-入场胶片条.jpg", quality=90)
print("contact + filmstrip saved")
