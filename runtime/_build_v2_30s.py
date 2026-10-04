"""_build_v2_30s.py — v7.2 修复版 30 秒样片。

修复两件事（均有量化证明）：
  A. 元素级入场动画：走真实逐帧链路 raster_renderer.draw_frame(t)，
     由 entrance_planner 的 lifecycle(enter{at,motion,dur,after}) 驱动，
     每个元素按时刻依次 fade / rise / pop 入场。
  B. 画面单调：修 common.PALETTES（恢复五套有差异的底色）+ emotion 兜底 +
     对齐本 SRT 的策略覆写（六种版式），并量化逐拍差异。

产出 /mnt/cos/artifacts/：
  attention-30s-v2.mp4
  v2-storyboard.png         每拍 settle 帧
  v2-entrance-sequence.png  首拍跨时刻入场过程
  v2-report.json            逐元素入场时刻表 + 逐拍差异 + 编码探测
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import numpy as np
from common import CANVAS_W as W, CANVAS_H as H

import srt_parser, beat_planner, visual_director, composition_planner
import entrance_planner, raster_renderer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRT = os.path.join(ROOT, "examples", "run", "attention-30s.srt")
OVR = os.path.join(ROOT, "examples", "run", "attention-30s.overrides.json")
OUT = "/mnt/cos/artifacts"
FPS = 24


def main():
    analysis = srt_parser.analyze(SRT)
    beats = beat_planner.plan_beats(analysis["cues"])
    ov = visual_director.load_overrides(OVR)
    _, dsl = visual_director.direct(beats, ov)
    rplan, _, _, audit = composition_planner.plan(dsl)
    ent = entrance_planner.plan(dsl)
    ea = entrance_planner.audit(ent)
    P = {b["beat_id"]: b for b in rplan["beats"]}
    E = {b["beat_id"]: b for b in ent["beats"]}

    print("layout=%s entrance=%s | beats=%d overrides=%d" %
          (audit["status"], ea["status"], len(dsl["beats"]), len(ov)))

    # ---- A) 逐元素入场时刻表 ----
    report = {"fps": FPS, "palette_fix": True, "beats": []}
    for b in dsl["beats"]:
        bid = b["beat_id"]; eb = E[bid]
        rows = []
        print("\n[%s] %.1f-%.1fs palette=%s strategy=%s handoff=%s" % (
            bid, b["start_sec"], b["end_sec"], b["palette"], b["strategy"],
            eb["handoff"].get("type")))
        for el in b["elements"]:
            lc = eb["lifecycle"].get(el["id"], {})
            e = lc.get("enter", {}); x = lc.get("exit")
            print("   %-20s %-9s enter@%+.2fs %-6s dur=%.2f after=%s%s" % (
                el["id"], el["type"], e.get("at", -1), e.get("motion", "?"),
                e.get("dur", 0), e.get("after", []),
                ("  exit@%+.2fs %s" % (x["at"], x["motion"])) if x else ""))
            rows.append({"id": el["id"], "type": el["type"], "role": el.get("role"),
                         "enter_at": e.get("at"), "enter_motion": e.get("motion"),
                         "enter_dur": e.get("dur"), "after": e.get("after", []),
                         "exit_at": (x or {}).get("at"), "exit_motion": (x or {}).get("motion")})
        report["beats"].append({"beat_id": bid, "palette": b["palette"],
                                "strategy": b["strategy"], "start": b["start_sec"],
                                "end": b["end_sec"], "elements": rows,
                                "cues": eb["cues"]})

    # ---- 逐帧渲染 MP4 ----
    ff = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    enc = subprocess.run([ff, "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    vcodec = "libx264" if "libx264" in enc else "mpeg4"
    total = sum(max(1, int(round((b["end_sec"] - b["start_sec"]) * FPS)))
                for b in dsl["beats"])
    mp4 = os.path.join(OUT, "attention-30s-v2.mp4")
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", vcodec, "-pix_fmt", "yuv420p"]
    cmd += (["-crf", "20", "-preset", "medium"] if vcodec == "libx264" else ["-q:v", "3"])
    cmd += ["-movflags", "+faststart", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    settles, seq = [], None
    prev = None; idx = 0
    for b in dsl["beats"]:
        bid = b["beat_id"]; pb, pe = P[bid], E[bid]
        dur = b["end_sec"] - b["start_sec"]; n = max(1, int(round(dur * FPS)))
        for k in range(n):
            img = raster_renderer.draw_frame(b, pb, pe, b["start_sec"] + k / FPS, prev=prev)
            proc.stdin.write(img.convert("RGB").tobytes()); idx += 1
        ts = b["start_sec"] + min(0.8 * dur, max(dur - 0.05, 0.0))
        settles.append((bid, raster_renderer.draw_frame(b, pb, pe, ts)))
        if seq is None:
            tl = [b["start_sec"] + r * dur for r in (0.02, 0.10, 0.22, 0.40, 0.62, 0.85)]
            seq = {"beat_id": bid, "offsets": [round(x - b["start_sec"], 2) for x in tl],
                   "imgs": [raster_renderer.draw_frame(b, pb, pe, x) for x in tl]}
        prev = (b, pb, pe)
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore")
    if proc.wait() != 0:
        sys.stderr.write(err[-1500:]); raise SystemExit("ffmpeg failed")

    # ---- 逐拍差异（证明不再单调）----
    arrs = [np.asarray(im.convert("RGB"), float) for _, im in settles]
    diffs = []
    print("\n逐拍 settle 帧两两平均绝对差：")
    for i in range(len(arrs)):
        for j in range(i + 1, len(arrs)):
            diffs.append(round(float(np.abs(arrs[i] - arrs[j]).mean()), 2))
    diffs_sorted = sorted(diffs)
    print("  min=%.2f median=%.2f max=%.2f  (修复前 01≈03≈05 仅 0.97-1.04)" %
          (diffs_sorted[0], diffs_sorted[len(diffs_sorted)//2], diffs_sorted[-1]))
    report["pairwise_settle_diff"] = diffs
    report["pairwise_diff_min"] = diffs_sorted[0]
    report["pairwise_diff_median"] = diffs_sorted[len(diffs_sorted)//2]

    # ---- 首拍入场过程：墨量随时刻上升 ----
    print("\n首拍元素入场过程（%s）ink_ratio @ %s:" % (seq["beat_id"], seq["offsets"]))
    ink = [round(raster_renderer.ink_stats(im)[0], 4) for im in seq["imgs"]]
    print("  ", ink)
    report["entrance_probe"] = {"beat_id": seq["beat_id"],
                                "t_offsets": seq["offsets"], "ink_ratio": ink}

    # ---- 联系表 / 序列图 ----
    def sheet(items, cols, out, label_prefix=""):
        gap, tw, th = 14, W // 2, H // 2
        rows = (len(items) + cols - 1) // cols
        sh = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap),
                       (246, 246, 244))
        dr = ImageDraw.Draw(sh)
        for i, (lab, im) in enumerate(items):
            r, c = divmod(i, cols)
            x, y = gap + c * (tw + gap), gap + r * (th + gap)
            sh.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
            dr.rectangle([x - 1, y - 1, x + tw, y + th], outline=(196, 196, 190))
            dr.text((x + 6, y + 6), lab, fill=(22, 22, 22))
        sh.save(out, quality=92); return sh.size

    sb = os.path.join(OUT, "v2-storyboard.png")
    sbsize = sheet([(b + " ·" + dict((x[0], x[1]) for x in []) .get(b, ""), im)
                    for b, im in settles], 2, sb)
    seqp = os.path.join(OUT, "v2-entrance-sequence.png")
    seqsize = sheet([("t+%.1fs" % seq["offsets"][i], im) for i, im in enumerate(seq["imgs"])],
                    3, seqp)

    dur = [l.strip() for l in subprocess.run([ff, "-i", mp4], capture_output=True,
           text=True).stderr.splitlines() if "Duration" in l]
    vid = [l.strip() for l in subprocess.run([ff, "-i", mp4], capture_output=True,
           text=True).stderr.splitlines() if "Video:" in l]
    report.update({"video": mp4, "vcodec": vcodec, "frames": idx, "size": "%dx%d" % (W, H),
                   "duration": dur[0] if dur else None, "video_stream": vid[0] if vid else None,
                   "storyboard": sb, "sequence": seqp})
    with open(os.path.join(OUT, "v2-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nMP4:", mp4, "%.1f KB" % (os.path.getsize(mp4) / 1024), "%d frames" % idx)
    print("DUR:", report["duration"])
    print("VID:", report["video_stream"])


if __name__ == "__main__":
    main()
