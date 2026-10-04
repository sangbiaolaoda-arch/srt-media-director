"""用参考帧构图语法（ref_frame）重渲 30s 样片。
内容 = 注意力/分心主题（与参考帧同源）；画面 = 复刻参考帧的构图代码。"""
import os, sys, glob, subprocess, shutil
sys.path.insert(0, "/mnt/work/srt-media-director/runtime")
import cairosvg
from PIL import Image
import ref_frame as R

W, H, FPS = 1280, 720, 15
OUT = "/mnt/work/refsample"
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

# ---- 7 拍内容（与 attention-30s.srt 对齐） ----
beats = []

# b1 establish：问句 + 副题 + 手机(红点3)
beats.append((4.0, R.frame_hero("为什么你总在分心？", "不是意志力差，是注意力被反复打断",
                               R.icon_phone(500, 200, 0.92, badge=3))))

# b2 statement
beats.append((4.0, R.frame_statement([("不是意志力差", False),
                                      ("是注意力被反复打断", True)], size=30)))

# b3 chain（灰节点，标题先行）
beats.append((4.5, R.frame_chain("一次通知，要付出三步代价", [
    ("通知响起",        R.icon_bell(123, 190, 1.0), False),
    ("专注被打断",      R.icon_focus_break(340, 186, 1.0), False),
    ("回到状态要时间",  R.icon_bar_half(557, 189, 1.0), False)])))

# b4 chain（中节点主，frame_02 复刻）
beats.append((4.5, R.frame_chain("一次通知，三步代价", [
    ("通知响起",        R.icon_bell(123, 190, 1.0), False),
    ("专注被打断",      R.icon_focus_break(340, 186, 1.0), True),
    ("回到状态要时间",  R.icon_bar_half(557, 189, 1.0), False)],
    caption="每次切换，都要重新找回刚才的思路")))

# b5 bar detail
beats.append((4.0, R.frame_bar_detail("回到状态要时间", 0.55,
                                      caption="重新进入专注不是瞬间完成的",
                                      label="恢复进度")))

# b6 contrast（frame_03 复刻）
beats.append((4.5, R.frame_compare(
    "离手机远一点，更能专注",
    {"label": "手机在手边", "bar": 54, "bar_accent": False,
     "icon_svg": R.icon_phone(246, 238, 0.24, col=R.INK)},
    {"label": "手机在另一个房间", "bar": 130, "bar_accent": True,
     "icon_svg": R.icon_door(562, 245, 1.0)},
    caption="示意图：柱高仅表示相对趋势，不代表具体数值")))

# b7 conclusion（大字）
beats.append((4.5, R.frame_hero("离手机远一点，更能专注", "把注意力还给当下要做的事",
                               R.icon_phone(500, 200, 0.92, badge=None))))

# ---- 逐拍渲染 PNG ----
def render(svg, path):
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path,
                     output_width=W, output_height=H)

imgs = []
for i, (_, svg) in enumerate(beats):
    p = f"{OUT}/beat_{i:02d}.png"
    render(svg, p)
    imgs.append(Image.open(p).convert("RGB"))

# ---- 配帧（跨拍溶解 0.4s） ----
cf = max(1, int(0.4 * FPS))
idx = 0
for i, (dur, _) in enumerate(beats):
    nf = max(1, int(round(dur * FPS)))
    cur = imgs[i]
    prev = imgs[i-1] if i > 0 else None
    for k in range(nf):
        if prev is not None and k < cf:
            a = (k + 1) / cf
            a = a*a*(3-2*a)
            frame = Image.blend(prev, cur, a)
        else:
            frame = cur
        frame.save(f"{OUT}/f_{idx:04d}.png")
        idx += 1
print("total frames:", idx)

# ---- 编码 MP4 ----
import imageio_ffmpeg
ff = imageio_ffmpeg.get_ffmpeg_exe()
mp4 = "/mnt/work/refsample-30s.mp4"
subprocess.run([ff, "-y", "-framerate", str(FPS), "-i", f"{OUT}/f_%04d.png",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("mp4:", os.path.getsize(mp4), "bytes")
shutil.copy(mp4, "/mnt/cos/artifacts/refsample-30s.mp4")

# ---- 联系表 ----
sel = [imgs[i] for i in range(len(imgs))]
tw = 560; gap = 10; cols = 3
sc = [im.resize((tw, int(im.height*tw/im.width))) for im in sel]
cw, ch = sc[0].size
rows = (len(sc)+cols-1)//cols
sheet = Image.new("RGB", (cols*cw+(cols+1)*gap, rows*ch+(rows+1)*gap), (255, 255, 255))
for i, im in enumerate(sc):
    r, c = divmod(i, cols)
    sheet.paste(im, (gap+c*(cw+gap), gap+r*(ch+gap)))
sheet.save("/mnt/cos/artifacts/refsample-30s-联系表.jpg", quality=90)
print("sheet:", sheet.size)
