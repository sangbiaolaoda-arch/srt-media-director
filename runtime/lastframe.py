"""Stage 6 CLI — 生成「末帧联系表」（廉价预览，只渲染每拍末帧）。

    python runtime/lastframe.py <out_dir> [--grid 3x4]

读取 <out_dir>/work 的 dsl / render-plan / entrance-plan，用与 L3 探针同一
个 draw_frame 渲染每拍末帧，拼成 contact sheet 写到 <out_dir>/lastframe-sheet.jpg。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beat_sheet  # noqa: E402
import raster_renderer  # noqa: E402


def _load(work, name):
    with open(os.path.join(work, name), encoding="utf-8") as f:
        return json.load(f)


def run(out_dir, grid=(3, 4)):
    work = os.path.join(out_dir, "work")
    dsl = _load(work, "visual-dsl.json")
    render_plan = _load(work, "render-plan.json")
    entrance = _load(work, "entrance-plan.json")
    p = beat_sheet.lastframe_sheet(
        dsl, render_plan, entrance, raster_renderer.draw_frame, out_dir, grid=grid)
    return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--grid", default="3x4")
    a = ap.parse_args()
    cols, rows = a.grid.lower().split("x")
    p = run(a.out_dir, (int(cols), int(rows)))
    print("末帧联系表: %s" % p)
