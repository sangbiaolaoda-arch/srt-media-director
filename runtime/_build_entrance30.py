"""_build_entrance30.py — 用真实「逐元素入场动画」链路产出 30 秒样片。

与上一版的关键区别：不再用静态截图 + 整帧推近，而是走
    SRT → beats → DSL → composition/entrance 规划 → raster_renderer.draw_frame(t)
逐帧渲染：每个元素按 lifecycle 的 enter{at,motion,dur,after} 依次入场
（fade/rise/pop），connector 逐笔 draw，chart_fill / bars_grow / pulse 有过程，
退场 sink/shrink/fade，跨拍 carry_over 位置插值 + 溶解。

产出：
  /mnt/cos/artifacts/attention-30s-entrance.mp4        （30s，真实元素入场）
  /mnt/cos/artifacts/entrance-30s-storyboard.png       （每拍 settle 帧）
  /mnt/cos/artifacts/entrance-30s-sequence.png         （单拍跨时刻=入场过程）
  /mnt/cos/artifacts/entrance-30s-timeline.json        （每元素入场时刻表）
"""
import os, sys, json, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from common import CANVAS_W as W, CANVAS_H as H, ensure_dir

import srt_parser, beat_planner, visual_director, composition_planner
import entrance_planner, raster_renderer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRT = os.path.join(ROOT, "examples", "run", "attention-30s.srt")
OVR = os.path.join(ROOT, "examples", "minimal", "director_overrides.json")
OUT = "/mnt/cos/artifacts"
FPS = 24


def build_layers(srt_path, overrides_path):
    analysis = srt_parser.analyze(srt_path)
    if analysis["errors"]:
        raise SystemExit("SRT errors: %s" % analysis["errors"])
    beats = beat_planner.plan_beats(analysis["cues"])
    ov = visual_director.load_overrides(overrides_path) if overrides_path else {}
    _, dsl = visual_director.direct(beats, ov)
    render_plan, _, _, audit = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    ea = entrance_planner.audit(entrance)
    return dsl, render_plan, entrance, audit, ea


def main():
    dsl, rplan, entrance, audit, ea = build_layers(SRT, OVR)
    print("layout audit:", audit["status"], "| entrance audit:", ea["status"])
    if ea["status"] != "PASS":
        print("  entrance issues:", ea["issues"][:6])

    plans = {b["beat_id"]: b for b in rplan["beats"]}
    ents = {b["beat_id"]: b for b in entrance["beats"]}

    # ---- 1) 打印每拍每个元素的入场时刻表（真实编排证据）----
    timeline = {"fps": FPS, "beats": []}
    for beat in dsl["beats"]:
        bid = beat["beat_id"]
        ent = ents[bid]
        rows = []
        print("\n[%s] %.1f–%.1fs  handoff=%s" % (
            bid, beat["start_sec"], beat["end_sec"], ent["handoff"].get("type")))
        for el in beat["elements"]:
            lc = ent["lifecycle"].get(el["id"], {})
            e = lc.get("enter", {})
            x = lc.get("exit")
            print("   %-22s %-7s enter@%.2fs %-7s dur=%.2f after=%s%s" % (
                el["id"], el["type"], e.get("at", -1), e.get("motion", "?"),
                e.get("dur", 0), e.get("after", []),
                ("  exit@%.2fs %s" % (x["at"], x["motion"])) if x else ""))
            rows.append({"id": el["id"], "type": el["type"],
                         "enter_at": e.get("at"), "enter_motion": e.get("motion"),
                         "enter_dur": e.get("dur"), "after": e.get("after", []),
                         "exit_at": (x or {}).get("at"),
                         "exit_motion": (x or {}).get("motion")})
        for c in ent["cues"]:
            print("   cue %s @%.2fs (%s)" % (c["cue_id"], c["at"], c["elements"]))
        timeline["beats"].append({"beat_id": bid, "start": beat["start_sec"],
                                  "end": beat["end_sec"],
                                  "handoff": ent["handoff"].get("type"),
                                  "elements": rows, "cues": ent["cues"],
                                  "events": ent["events"]})

    # ---- 2) 逐帧渲染（draw_frame 驱动元素入场）----
    ff = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    enc = subprocess.run([ff, "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    vcodec = "libx264" if "libx264" in enc else "mpeg4"
    total = sum(max(1, int(round((b["end_sec"] - b["start_sec"]) * FPS)))
                for b in dsl["beats"])
    print("\nencode %s · %d beats · %d frames @%dfps" %
          (vcodec, len(dsl["beats"]), total, FPS))

    mp4 = os.path.join(OUT, "attention-30s-entrance.mp4")
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", vcodec, "-pix_fmt", "yuv420p"]
    cmd += (["-crf", "20", "-preset", "medium"] if vcodec == "libx264" else ["-q:v", "3"])
    cmd += ["-movflags", "+faststart", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    settles, seq_imgs = [], {}
    prev = None
    idx = 0
    for beat in dsl["beats"]:
        bid = beat["beat_id"]
        pb, pe = plans[bid], ents[bid]
        dur = beat["end_sec"] - beat["start_sec"]
        n = max(1, int(round(dur * FPS)))
        for k in range(n):
            t = beat["start_sec"] + k / FPS
            img = raster_renderer.draw_frame(beat, pb, pe, t, prev=prev)
            proc.stdin.write(img.convert("RGB").tobytes())
            idx += 1
        # settle 帧
        ts = beat["start_sec"] + min(0.80 * dur, max(dur - 0.05, 0.0))
        settles.append((bid, raster_renderer.draw_frame(beat, pb, pe, ts)))
        # 入场序列：该拍内 6 个时刻
        if bid == dsl["beats"][0]["beat_id"]:
            ts_list = [beat["start_sec"] + r * dur for r in (0.02, 0.10, 0.22, 0.40, 0.62, 0.85)]
            seq_imgs[bid] = [raster_renderer.draw_frame(beat, pb, pe, tt) for tt in ts_list]
            timeline["sequence_probe"] = {"beat_id": bid,
                                          "t_offsets": [round(x - beat["start_sec"], 2) for x in ts_list]}
        prev = (beat, pb, pe)
        print("  %s -> %d/%d" % (bid, idx, total))
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore")
    if proc.wait() != 0:
        sys.stderr.write(err[-1500:]); raise SystemExit("ffmpeg failed")

    # ---- 3) 每拍 settle 联系表 ----
    def sheet(items, cols, out, labelfn=None):
        gap, tw, th = 14, W // 2, H // 2
        rows = (len(items) + cols - 1) // cols
        sh = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap),
                       (248, 248, 246))
        dr = ImageDraw.Draw(sh)
        for i, (lab, im) in enumerate(items):
            r, c = divmod(i, cols)
            x, y = gap + c * (tw + gap), gap + r * (th + gap)
            sh.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
            dr.rectangle([x - 1, y - 1, x + tw, y + th], outline=(196, 196, 190))
            dr.text((x + 6, y + 6), lab, fill=(24, 24, 24))
        sh.save(out, quality=92)
        return sh.size

    sb = os.path.join(OUT, "entrance-30s-storyboard.png")
    sbsize = sheet([(b, im) for b, im in settles], 2, sb)

    # 入场序列图（一拍跨时刻，横向 3x2）
    seq = os.path.join(OUT, "entrance-30s-sequence.png")
    seqsize = None
    for bid, imgs in seq_imgs.items():
        toff = timeline["sequence_probe"]["t_offsets"]
        items = [("t+%.1fs" % toff[i], im) for i, im in enumerate(imgs)]
        seqsize = sheet(items, 3, seq)

    # ---- 4) 入场过程量化：一拍内墨量随时刻增长（证明元素逐个进来）----
    probe = {}
    for bid, imgs in seq_imgs.items():
        vals = [round(raster_renderer.ink_stats(im)[0], 4) for im in imgs]
        probe[bid] = vals
        print("\n入场过程 ink_ratio @", timeline["sequence_probe"]["t_offsets"], "=", vals)
    timeline["sequence_ink_ratio"] = probe

    with open(os.path.join(OUT, "entrance-30s-timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    print("\nMP4:", mp4, "%.1f KB" % (os.path.getsize(mp4) / 1024))
    print("storyboard:", sb, sbsize, "| sequence:", seq, seqsize)


if __name__ == "__main__":
    main()
