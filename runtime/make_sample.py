"""Sample-first workflow（skill 00-core-contract：样例优先，禁止直接渲全片）.

    python runtime/make_sample.py 30                 # 前 30 秒：编译 + 门禁 + 抽帧 + 拼图
    python runtime/make_sample.py 60 --srt path.srt  # 指定输入
    python runtime/make_sample.py 30 --no-render     # 只编译 + 跑门禁（秒级）

产出在 <out>/（默认 sample/）：work/*.json · preview/<beat>/*.png · sheet.jpg ·
film/index.html。
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline  # noqa: E402
import srt_parser  # noqa: E402
from common import COLORS, ensure_dir, font, hex2rgb  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRT = os.path.join(ROOT, "examples", "minimal", "attention.srt")
DEFAULT_OVERRIDES = os.path.join(ROOT, "examples", "minimal",
                                 "director_overrides.json")


def fmt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def trim_srt(src, dst, seconds):
    """裁剪前 N 秒字幕。SRT 仍是唯一时间真值——只做裁断，不重新估算时间。"""
    analysis = srt_parser.analyze(src)
    kept = [c for c in analysis["cues"] if c["start"] < seconds]
    if not kept:
        raise SystemExit("裁剪后没有字幕：seconds=%s" % seconds)
    with open(dst, "w", encoding="utf-8") as f:
        for i, c in enumerate(kept, 1):
            f.write("%d\n%s --> %s\n%s\n\n"
                    % (i, fmt_time(c["start"]), fmt_time(c["end"]), c["text"]))
    return len(kept)


def contact_sheet(preview_dir, out_path, cols=3):
    """把每拍探针帧拼成一张联系表，便于 40 秒级的「改 → 看」循环。"""
    from PIL import Image, ImageDraw
    paths = sorted(glob.glob(os.path.join(preview_dir, "*", "*.png")))
    if not paths:
        return None
    tw, th, pad, label_h = 320, 180, 12, 22
    rows = (len(paths) + cols - 1) // cols
    sheet_w = cols * tw + (cols + 1) * pad
    sheet_h = rows * (th + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), hex2rgb(COLORS["paper"]))
    dr = ImageDraw.Draw(sheet)
    fnt = font(16)
    for i, p in enumerate(paths):
        img = Image.open(p).convert("RGB").resize((tw, th))
        x = pad + (i % cols) * (tw + pad)
        y = pad + (i // cols) * (th + label_h + pad)
        sheet.paste(img, (x, y))
        label = "%s · %s" % (os.path.basename(os.path.dirname(p)),
                             os.path.basename(p))
        dr.text((x + 2, y + th + 2), label, font=fnt,
                fill=hex2rgb(COLORS["ink"]))
    sheet.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="样例优先：只跑前 N 秒的完整链路")
    ap.add_argument("seconds", type=float, nargs="?", default=30.0)
    ap.add_argument("--srt", default=DEFAULT_SRT)
    ap.add_argument("--overrides", default=DEFAULT_OVERRIDES)
    ap.add_argument("--out", default=os.path.join(ROOT, "sample"))
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    work = ensure_dir(os.path.join(args.out, "work"))
    trimmed = os.path.join(work, "input.trimmed.srt")
    n = trim_srt(args.srt, trimmed, args.seconds)
    print("样例裁剪：%d cues（前 %.0f 秒）→ %s" % (n, args.seconds, trimmed))

    report = pipeline.run(trimmed, args.out, overrides_path=args.overrides,
                          render_previews=not args.no_render)
    if not args.no_render:
        sheet = contact_sheet(os.path.join(args.out, "preview"),
                              os.path.join(args.out, "sheet.jpg"))
        if sheet:
            print("联系表: %s" % sheet)
    print("播放器: %s" % os.path.join(args.out, "film", "index.html"))
    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
