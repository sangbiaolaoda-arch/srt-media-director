"""Stage 6 工具（v6.0）：

- ``beat_sheet(dsl, contracts, path)``  → 渲染前自动生成「节拍表」（纸面评审）。
- ``lastframe_sheet(...)``              → 只渲染每拍末帧并拼成一张图（低成本预览）。

节拍表对应 Seedance 的分镜表：在花渲染成本之前，用纸面检查结构。
"""
import os

import contracts


def _claim_of(beat):
    return beat.get("visual_claim") or beat.get("claim") or ""


def beat_sheet(dsl, cbeats, path):
    """生成 Markdown + JSON 节拍表。返回写的路径。"""
    rows = []
    cmap = {c["beat_id"]: c for c in cbeats}
    for b in dsl["beats"]:
        c = cmap.get(b["beat_id"], {})
        tr = c.get("transition_in", {})
        es = c.get("end_state", {})
        rows.append({
            "beat": b["beat_id"],
            "claim": _claim_of(b),
            "primary": c.get("primary"),
            "path": " > ".join(c.get("attention_path", [])),
            "in": tr.get("type", ""),
            "reason": tr.get("reason", ""),
            "end_frame": ",".join(es.get("visible", [])),
            "hold_ms": es.get("hold_ms", 0),
            "ambient": ",".join((c.get("ambient") or {}).keys()),
        })
    md = ["# 节拍表（Beat Sheet）",
          "",
          "| " + " | ".join(["beat", "视觉命题", "primary", "视线路径", "进入",
                              "末帧可见", "hold(ms)", "ambient"]) + " |",
          "|" + "---|" * 8]
    for r in rows:
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["beat"], r["claim"][:22], r["primary"] or "", r["path"],
            r["in"], r["end_frame"][:28], r["hold_ms"], r["ambient"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return path, rows


def lastframe_sheet(dsl, render_plan, entrance, draw_frame, out_dir,
                    grid=(3, 4), thumb_w=360):
    """只渲染每拍末帧，拼成联系表（廉价预览）。"""
    from PIL import Image  # noqa
    boxes = {b["beat_id"]: b for b in render_plan["beats"]}
    ents = {b["beat_id"]: b for b in entrance["beats"]}
    frames = []
    for b in dsl["beats"]:
        t = max(b["start_sec"], b["end_sec"] - 0.05)
        img = draw_frame(b, boxes[b["beat_id"]], ents[b["beat_id"]], t, prev=None)
        frames.append((b["beat_id"], img.convert("RGB")))
    if not frames:
        return None
    cols, rows_n = grid
    cell_w = thumb_w
    cell_h = int(cell_w * frames[0][1].height / frames[0][1].width)
    sheet = Image.new("RGB", (cols * cell_w, rows_n * (cell_h + 18)), (255, 255, 255))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    for i, (bid, img) in enumerate(frames):
        r, c = divmod(i, cols)
        if r >= rows_n:
            break
        x, y = c * cell_w, r * (cell_h + 18)
        sheet.paste(img.resize((cell_w, cell_h)), (x, y))
        dr.text((x + 4, y + cell_h + 3), bid, fill=(40, 40, 40))
    p = os.path.join(out_dir, "lastframe-sheet.jpg")
    sheet.save(p, quality=62, optimize=True)
    return p


def anti_cliche_gate(dsl):
    return contracts.check_claims(dsl)
