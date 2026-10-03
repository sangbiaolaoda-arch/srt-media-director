#!/usr/bin/env python3
"""SRT Media Director — 命令行入口.

    python cli.py input.srt --out out-dir [--overrides overrides.json] [--no-render]

流水线：SRT → 语义分析 → Beat 基线 → 导演层（Visual Plan + DSL）→
构图求解（Render Plan + 布局门禁）→ 入场编排（Entrance Plan + 节奏门禁）→
HTML 播放器（film/index.html，只读产物）→ 分层校验（validation-report.json）。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "runtime"))

import pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        prog="srt-media-director",
        description="SRT → 语义 Beat → 视觉计划 → DSL → 布局/入场 → HTML 播放器 → 分层校验")
    ap.add_argument("srt", help="输入 SRT（唯一时间真值）")
    ap.add_argument("--out", default=None, help="输出目录（默认 <srt名>-out/）")
    ap.add_argument("--overrides", default=None,
                    help="导演层人工覆写 JSON（可选；格式见 "
                         "examples/minimal/director_overrides.json）")
    ap.add_argument("--no-render", action="store_true",
                    help="跳过 L3 光栅探针（只跑 schema/L1）")
    args = ap.parse_args()

    out = args.out or (os.path.splitext(os.path.basename(args.srt))[0] + "-out")
    report = pipeline.run(args.srt, out, overrides_path=args.overrides,
                          render_previews=not args.no_render)
    print("\n产物目录: %s" % os.path.abspath(out))
    print("播放器:   %s" % os.path.abspath(os.path.join(out, "film", "index.html")))
    print("校验报告: %s" % os.path.abspath(
        os.path.join(out, "work", "validation-report.json")))
    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
