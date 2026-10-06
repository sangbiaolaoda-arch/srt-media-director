"""把 beat-audit JSON 渲染成便于查看的单文件 HTML（供人眼逐条挑错）。"""
import glob
import html
import json
import os
import sys


def esc(s):
    return html.escape(str(s))


def render_one(data, title):
    beats = data["beats"]
    bounds = data["boundaries"]
    sus = [b for b in bounds if b.get("flags")]

    parts = []
    parts.append('<section class="doc">')
    parts.append('<h1>%s</h1>' % esc(title))
    parts.append('<p class="meta">来源 <code>%s</code> · %d 拍 · %d 处边界 · '
                 '<b class="warn">%d 处可疑</b></p>' % (
                     esc(data["source"]), len(beats), len(bounds), len(sus)))

    parts.append('<h2>一、可疑边界（重点看）</h2>')
    if not sus:
        parts.append('<p>（无自动命中的可疑边界）</p>')
    for b in sus:
        parts.append('<div class="bound">')
        parts.append('<div class="bt">⚠️ %s</div>' % esc(b["between"]))
        parts.append('<div class="l">左句 <code>#%02d</code>：%s</div>' % (
            b["left_cue"], esc(b["left_text"])))
        parts.append('<div class="r">右句 <code>%02d</code>：%s</div>' % (
            b["right_cue"], esc(b["right_text"])))
        parts.append('<ul>')
        for f in b["flags"]:
            parts.append('<li>%s</li>' % esc(f))
        parts.append('</ul>')
        parts.append('</div>')

    parts.append('<h2>二、全部边界对照</h2>')
    parts.append('<table><thead><tr><th>边界</th><th>左拍末句</th>'
                 '<th>右拍首句</th><th>右句时长</th><th>硬约束</th>'
                 '<th>标记</th></tr></thead><tbody>')
    for b in bounds:
        cls = ' class="hit"' if b["flags"] else ""
        parts.append('<tr%s><td>%s</td><td>%s</td><td>%s</td><td>%.2fs</td>'
                     '<td>%s</td><td>%s</td></tr>' % (
                         cls, esc(b["between"]), esc(b["left_text"]),
                         esc(b["right_text"]), b["right_dur"],
                         "✅" if b["protected_by_hard"] else "—",
                         esc("；".join(b["flags"])) if b["flags"] else "—"))
    parts.append('</tbody></table>')

    parts.append('<h2>三、逐拍明细</h2>')
    for r in beats:
        parts.append('<details><summary>%s · %.2f–%.2fs（%.2fs）· %s'
                     '</summary>' % (
                         esc(r["beat_id"]), r["start_sec"], r["end_sec"],
                         r["duration_sec"], esc(r["role"])))
        parts.append('<ul class="cues">')
        for c in r["cues"]:
            tag = (' <span class="pair">[%s]</span>' %
                   esc(",".join(c["pairs"]))) if c.get("pairs") else ""
            parts.append('<li><code>#%02d</code> %.2f–%.2fs（%.2fs） %s%s'
                         '</li>' % (c["id"], c["start"], c["end"],
                                    c["dur"], esc(c["text"]), tag))
        parts.append('</ul>')
        parts.append('<p class="join">拼接：%s</p>' % esc(r["narration"]))
        parts.append('</details>')
    parts.append('</section>')
    return "\n".join(parts)


CSS = """
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
 background:#E9E4DE;color:#26221E;margin:0;padding:24px}
.doc{max-width:1100px;margin:0 auto 40px;background:#F4EFE6;border:1px solid #D8B4A8;
 border-radius:10px;padding:24px 28px}
h1{font-size:24px;margin:0 0 6px} h2{font-size:19px;margin:26px 0 10px;
 border-bottom:2px solid #E14D49;padding-bottom:6px}
.meta{color:#5F564B;font-size:13px} .warn{color:#A8281F}
.bound{background:#FBF3F0;border-left:4px solid #A8281F;padding:10px 14px;
 margin:10px 0;border-radius:6px}
.bound .bt{font-weight:700;color:#A8281F;margin-bottom:4px}
.bound .l{color:#26221E}.bound .r{color:#26221E}
.bound ul{margin:6px 0 0 0;padding-left:20px;color:#5F564B;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}
th,td{border:1px solid #D8B4A8;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#F0D8CC} tr.hit{background:#FBE9E4}
code{background:#EFE7DE;padding:1px 5px;border-radius:4px;color:#A8281F}
details{margin:8px 0;background:#EFE7DE;border-radius:6px;padding:8px 12px}
summary{cursor:pointer;font-weight:600}
.cues{padding-left:20px;font-size:13px;color:#33374D}
.pair{color:#2E5A4A} .join{font-size:13px;color:#5F564B;margin:6px 0 0}
"""


def main():
    files = sys.argv[1:-1]
    out = sys.argv[-1]
    bodies = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        title = "Beat 拆分对照 · %s" % os.path.basename(d["source"])
        bodies.append(render_one(d, title))
    doc = ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
           "<title>Beat 拆分对照</title><style>%s</style></head><body>%s"
           "</body></html>" % (CSS, "\n".join(bodies)))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("→ %s (%d docs)" % (out, len(bodies)))


if __name__ == "__main__":
    main()
