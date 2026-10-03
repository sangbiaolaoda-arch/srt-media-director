"""Render the minimal example to a real MP4 sample video.

    python runtime/render_video.py                        # 38s 完整示例
    python runtime/render_video.py --fps 15 --out out.mp4

Frames are rendered by the SAME raster probe used for L3 validation
(raster_renderer.draw_frame) and piped raw to ffmpeg (imageio-ffmpeg static
binary or system ffmpeg). The original SRT is embedded as a soft subtitle
track (mov_text), so the video is self-explanatory while the visuals stay
pure — no burned-in captions on top of the composition.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beat_planner  # noqa: E402
import composition_planner  # noqa: E402
import entrance_planner  # noqa: E402
import raster_renderer  # noqa: E402
import srt_parser  # noqa: E402
import visual_director  # noqa: E402
from common import CANVAS_H, CANVAS_W, ensure_dir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRT = os.path.join(ROOT, "examples", "minimal", "attention.srt")
DEFAULT_OVERRIDES = os.path.join(ROOT, "examples", "minimal",
                                 "director_overrides.json")


def find_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    from shutil import which
    ff = which("ffmpeg")
    if not ff:
        raise SystemExit("no ffmpeg available (pip install imageio-ffmpeg)")
    return ff


def pick_vcodec(ff):
    out = subprocess.run([ff, "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    return "libx264" if "libx264" in out else "mpeg4"


def build_layers(srt_path, overrides_path):
    """完整走一遍流水线各层（与 self_test 门禁同源），返回渲染所需结构。"""
    analysis = srt_parser.analyze(srt_path)
    if analysis["errors"]:
        raise SystemExit("SRT errors: %s" % analysis["errors"])
    beats = beat_planner.plan_beats(analysis["cues"])
    ov = (visual_director.load_overrides(overrides_path)
          if overrides_path else {})
    _, dsl = visual_director.direct(beats, ov)
    render_plan, _, _, audit = composition_planner.plan(dsl)
    if audit["status"] != "PASS":
        raise SystemExit("layout audit failed: %s" % audit["issues"])
    entrance = entrance_planner.plan(dsl)
    ea = entrance_planner.audit(entrance)
    if ea["status"] != "PASS":
        raise SystemExit("entrance audit failed: %s" % ea["issues"])
    plans = {b["beat_id"]: b for b in render_plan["beats"]}
    ents = {b["beat_id"]: b for b in entrance["beats"]}
    return dsl, plans, ents


def main():
    ap = argparse.ArgumentParser(description="把示例渲染成 MP4 样例视频")
    ap.add_argument("--srt", default=DEFAULT_SRT)
    ap.add_argument("--overrides", default=DEFAULT_OVERRIDES)
    ap.add_argument("--out", default=os.path.join(
        ROOT, "sample-video", "attention-sample.mp4"))
    ap.add_argument("--fps", type=int, default=15)
    args = ap.parse_args()

    dsl, plans, ents = build_layers(args.srt, args.overrides)
    ff = find_ffmpeg()
    vcodec = pick_vcodec(ff)
    total = sum(max(1, int(round((b["end_sec"] - b["start_sec"]) * args.fps)))
                for b in dsl["beats"])
    print("编码器: %s (%s) · %d beats · %d frames @ %dfps"
          % (os.path.basename(ff), vcodec, len(dsl["beats"]), total, args.fps))

    ensure_dir(os.path.dirname(args.out))
    cmd = [ff, "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (CANVAS_W, CANVAS_H), "-r", str(args.fps),
           "-i", "-",
           "-i", args.srt, "-map", "0:v", "-map", "1:s?",
           "-c:v", vcodec, "-pix_fmt", "yuv420p",
           "-crf", "20", "-preset", "medium",
           "-c:s", "mov_text", "-metadata:s:s:0", "language=chi",
           "-movflags", "+faststart", args.out]
    if vcodec == "mpeg4":  # 静态构建万一没有 libx264 的兜底
        i = cmd.index("-crf")
        cmd[i:i + 4] = ["-q:v", "3"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    idx = 0
    prev = None
    try:
        for beat in dsl["beats"]:
            pb, pe = plans[beat["beat_id"]], ents[beat["beat_id"]]
            n = max(1, int(round((beat["end_sec"] - beat["start_sec"])
                                 * args.fps)))
            for k in range(n):
                t = beat["start_sec"] + k / args.fps
                img = raster_renderer.draw_frame(beat, pb, pe, t, prev=prev)
                proc.stdin.write(img.convert("RGB").tobytes())
                idx += 1
            prev = (beat, pb, pe)  # 跨拍连续：下一拍首 0.45s 溶出本拍末态
            print("  %s → %d/%d frames" % (beat["beat_id"], idx, total))
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode("utf-8", "ignore")
    if proc.wait() != 0:
        sys.stderr.write(err[-2000:])
        raise SystemExit("ffmpeg encode failed")
    size_mb = os.path.getsize(args.out) / 1e6
    print("完成: %s (%.2f MB)" % (args.out, size_mb))


if __name__ == "__main__":
    main()
