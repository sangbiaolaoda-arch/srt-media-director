"""_build_sample30.py — 用新六包架构产出 30 秒真实样片。

链路（全部真实执行，不造假）：
    VisualIntent ×6 → Compiler(compile_intent + constraints)
        → Render(screenshot via chromium) → Critic(判决 + 修复路由)
        → PASS 光栅 → 确定性运镜/叠化 → 30s MP4

产出：
    /mnt/cos/artifacts/attention-sample-30s.mp4
    /mnt/cos/artifacts/sample30-storyboard.png
    /mnt/cos/artifacts/sample30-report.json
"""
import os, sys, json, subprocess, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime"))
from PIL import Image
import director_loop as DL

OUT = "/mnt/cos/artifacts"
W, H = 1280, 720
FPS = 24
TARGET_SEC = 30.0

# ---- 30 秒分镜：6 个 Beat，各 5 秒（语义意图，零坐标）----------------------
BEATS = [
    {"beat_id": "b1_flood", "visual_claim": "信息洪流向你涌来",
     "grammar": ["establish"], "focal_point": "viewer",
     "relationship": [{"from": "stream", "relation": "bound_to", "to": "viewer"}],
     "density": 0.55, "silence": False, "motion_intent": "establish",
     "entities": ["stream", "viewer"]},
    {"beat_id": "b2_split", "visual_claim": "专注与分心此消彼长",
     "grammar": ["contrast"], "focal_point": "focus",
     "relationship": [{"from": "focus", "relation": "contrast", "to": "distraction"}],
     "density": 0.45, "silence": False, "motion_intent": "contrast_then_focus",
     "entities": ["focus", "distraction"]},
    {"beat_id": "b3_cost", "visual_claim": "一次打断，三重代价",
     "grammar": ["causality", "progression"], "focal_point": "interrupt",
     "relationship": [{"from": "notify", "relation": "causes", "to": "interrupt"},
                      {"from": "interrupt", "relation": "flow_to", "to": "recover"}],
     "density": 0.5, "silence": False, "motion_intent": "morph",
     "entities": ["notify", "interrupt", "recover"]},
    {"beat_id": "b4_accum", "visual_claim": "微小行动累积成改变",
     "grammar": ["accumulation", "trajectory", "threshold"], "focal_point": "trajectory",
     "relationship": [{"from": "small_actions", "relation": "flow_to", "to": "trajectory"}],
     "density": 0.6, "silence": False, "motion_intent": "accumulate_then_reveal",
     "entities": ["small_actions", "trajectory", "threshold"]},
    {"beat_id": "b5_clue", "visual_claim": "从杂讯里浮出线索",
     "grammar": ["progression"], "focal_point": "clue",
     "relationship": [{"from": "noise", "relation": "flow_to", "to": "clue"}],
     "density": 0.5, "silence": False, "motion_intent": "reveal",
     "entities": ["noise", "clue"]},
    {"beat_id": "b6_now", "visual_claim": "回到当下，一次只做一件事",
     "grammar": ["emphasis"], "focal_point": "now",
     "relationship": [{"from": "one_thing", "relation": "emphasis", "to": "now"}],
     "density": 0.4, "silence": False, "motion_intent": "focus",
     "entities": ["now", "one_thing"]},
]


def render_intents():
    d = tempfile.mkdtemp(prefix="sample30_")
    summary = DL.run_intents(BEATS, d, max_repair=3, shot_scale=2)
    return summary


def kenburns(base, t):
    """确定性运镜：缓慢推近 + 轻微横移（t∈[0,1)）。"""
    z = 1.0 + 0.07 * t
    cw, ch = int(W / z), int(H / z)
    cx = (W - cw) // 2 + int((0.5 - t) * 0.05 * W)
    cy = (H - ch) // 2
    cx = max(0, min(W - cw, cx)); cy = max(0, min(H - ch, cy))
    return base.crop((cx, cy, cx + cw, cy + ch)).resize((W, H), Image.LANCZOS)


def build_video(stills, out_path):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    encoders = subprocess.run([ff, "-hide_banner", "-encoders"],
                              capture_output=True, text=True).stdout
    vcodec = "libx264" if "libx264" in encoders else "mpeg4"

    total = int(round(TARGET_SEC * FPS))            # 720
    nb = len(stills)
    cf = 12                                          # 0.5s 叠化
    n_i = (total + cf * (nb - 1)) // nb              # 每拍帧数
    # 逐拍生成带运镜的帧
    per_beat = []
    for img in stills:
        base = img.resize((W, H), Image.LANCZOS)
        frames = [kenburns(base, k / max(1, n_i - 1)) for k in range(n_i)]
        per_beat.append(frames)

    # 叠化拼接
    out = list(per_beat[0])
    for i in range(1, nb):
        nxt = per_beat[i]
        for k in range(cf):
            a = out[-cf + k]
            out[-cf + k] = Image.blend(a, nxt[k], (k + 1) / (cf + 1))
        out.extend(nxt[cf:])

    frames_written = len(out)
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
           "-c:v", vcodec, "-pix_fmt", "yuv420p"]
    if vcodec == "libx264":
        cmd += ["-crf", "20", "-preset", "medium"]
    else:
        cmd += ["-q:v", "3"]
    cmd += ["-movflags", "+faststart", out_path]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for f in out:
            proc.stdin.write(f.convert("RGB").tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode("utf-8", "ignore")
    if proc.wait() != 0:
        sys.stderr.write(err[-2000:])
        raise SystemExit("ffmpeg encode failed")
    return vcodec, frames_written, out_path


def contact_sheet(items, out_path):
    gap = 16
    cols = 2
    rows = (len(items) + cols - 1) // cols
    tw, th = W // 2, H // 2
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap,
                              rows * th + (rows + 1) * gap), (250, 250, 248))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    for idx, (bid, im) in enumerate(items):
        r, c = divmod(idx, cols)
        x = gap + c * (tw + gap); y = gap + r * (th + gap)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        dr.rectangle([x - 1, y - 1, x + tw, y + th], outline=(200, 200, 195))
        dr.text((x + 6, y + 6), bid, fill=(30, 30, 30))
    sheet.save(out_path, quality=92)
    return out_path, sheet.size


def main():
    summary = render_intents()
    print("closed-loop: %d/%d PASS" % (summary["passed"], summary["total"]))
    report = {"passed": summary["passed"], "total": summary["total"],
              "beats": []}
    stills, items = [], []
    for r in summary["results"]:
        issues = [i.get("code") for i in (r["trace"][-1].get("issues", []) if r["trace"] else [])]
        raster = r["trace"][-1].get("raster", {}) if r["trace"] else {}
        print("  %-9s %-5s backend=%s attempts=%d ink=%s" %
              (r["beat_id"], r["verdict"], r["backend"], r["attempts"],
               raster.get("ink_ratio")))
        report["beats"].append({"beat_id": r["beat_id"], "verdict": r["verdict"],
                                "backend": r["backend"], "attempts": r["attempts"],
                                "issues": issues, "ink_ratio": raster.get("ink_ratio")})
        if r["png"] and os.path.exists(r["png"]):
            im = Image.open(r["png"]).convert("RGB")
            stills.append(im)
            items.append((r["beat_id"], im))

    if len(stills) < 2:
        raise SystemExit("stills insufficient: %d" % len(stills))

    vcodec, fw, mp4 = build_video(stills, os.path.join(OUT, "attention-sample-30s.mp4"))
    sheet_path, sheet_size = contact_sheet(items, os.path.join(OUT, "sample30-storyboard.png"))

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run([ff, "-i", mp4], capture_output=True, text=True).stderr
    dur = [ln.strip() for ln in probe.splitlines() if "Duration" in ln]
    vid = [ln.strip() for ln in probe.splitlines() if "Video:" in ln]

    report.update({"video": mp4, "vcodec": vcodec, "frames": fw, "fps": FPS,
                   "size": "%dx%d" % (W, H), "duration_target_sec": TARGET_SEC,
                   "ffprobe_duration": dur[0] if dur else None,
                   "ffprobe_video": vid[0] if vid else None,
                   "storyboard": sheet_path, "storyboard_size": sheet_size})
    with open(os.path.join(OUT, "sample30-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("VIDEO:", mp4, "%.1f KB" % (os.path.getsize(mp4) / 1024), vcodec, fw, "frames")
    print("DUR:", report["ffprobe_duration"])
    print("VID:", report["ffprobe_video"])


if __name__ == "__main__":
    main()
