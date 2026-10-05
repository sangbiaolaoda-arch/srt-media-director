"""SVG art library（skill 04/08：部分图像以 SVG 绘画）.

每种画法返回一段 SVG 字符串（viewBox 0 0 100 100，`{COLOR}` 为颜色占位符）。
- motif：具象主体图形（全部非拟人——本仓库不出现人物形象）
- decor：装饰附体（点阵 / 圆环 / 刻度 / 图表 / 小物件 …，均非拟人）

v4.4 扩库（回应「画面太素 / 只画了简单图标」）：
- motif 5 → 20：新增图表类（柱状 / 折线 / 环形进度）、小物件类
  （钥匙 / 信封 / 日历 / 里程碑 / 奖杯 / 罗盘 / 天平 / 灯泡 / 书签 / 锁 /
   沙漏 / 地图针 / 齿轮 / 靶心 / 旗帜）
- decor 4 → 16：新增波形 / 散点 / 方括号 / 半调点阵 / 交叉网格 / 螺旋 /
  迷你柱 / 标尺 / 加号阵 / 轨道 / 箭头链 / 里程碑点

两条机器纪律：
- audit_svg()：越界审计——所有坐标必须落在 viewBox [-6, 106] 内
  （SVG 默认 overflow:hidden，越界不是画出去而是被裁掉）；
- 双侧实现：PIL 探针经 cairosvg 光栅化，HTML 播放器以 data-URL 内嵌同一字符串，
  保证 L3 探针帧与播放画面是同一幅画。
"""
import functools
import io
import math
import re

import cairosvg
from PIL import Image

# 晶格坐标只有一个实现（procedural_canonical.layout）——装饰生成器不再手写双重循环。
from procedural_canonical import layout as _layout
_lattice = _layout.lattice
_lattice_idx = _layout.lattice_idx

VIEWBOX = 100

_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
         'fill="none" stroke="{COLOR}" stroke-width="5" stroke-linecap="round" '
         'stroke-linejoin="round">')
_HEADF = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
          'fill="none" stroke="{COLOR}">')


# ---------------------------------------------------------------- motifs

def _phone():
    """手机 + 信号波纹 + 通知点。"""
    return (_HEAD +
            '<rect x="28" y="8" width="40" height="84" rx="9" stroke-width="5"/>'
            '<rect x="35" y="22" width="26" height="54" stroke-width="2.5"/>'
            '<line x1="42" y1="15" x2="54" y2="15" stroke-width="3"/>'
            '<circle cx="48" cy="84" r="2.6" fill="{COLOR}" stroke="none"/>'
            '<path d="M76 30 a16 16 0 0 1 0 22" stroke-width="3"/>'
            '<path d="M84 24 a26 26 0 0 1 0 34" stroke-width="3"/>'
            '<circle cx="64" cy="26" r="4.5" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _moon():
    """新月 + 星星。"""
    star = ('<path d="M{cx} {y1} L{x1} {cy} L{cx} {y2} L{x2} {cy} Z" '
            'fill="{{COLOR}}" stroke="none"/>')
    stars = "".join(star.format(cx=cx, cy=cy, x1=cx - r, x2=cx + r,
                                y1=cy - r * 2, y2=cy + r * 2)
                    for cx, cy, r in ((74, 18, 3.2), (86, 34, 2.2), (70, 44, 1.8)))
    return (_HEAD +
            '<path d="M60 10 A40 40 0 1 0 60 90 A31 31 0 1 1 60 10 Z" '
            'fill="{COLOR}" stroke="none"/>'
            + stars + '</svg>')


def _shield():
    """盾牌 + 对勾。"""
    return (_HEAD +
            '<path d="M50 8 L84 20 V50 C84 72 68 86 50 93 C32 86 16 72 16 50 V20 Z"/>'
            '<path d="M35 50 L47 62 L68 38" stroke-width="6"/>'
            '</svg>')


def _clock():
    """时钟（12 刻度 + 双指针）。"""
    ticks = []
    for i in range(12):
        a = math.radians(i * 30)
        x1 = 50 + 34 * math.sin(a)
        y1 = 50 - 34 * math.cos(a)
        x2 = 50 + 28 * math.sin(a)
        y2 = 50 - 28 * math.cos(a)
        ticks.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="2.5"/>'
                     % (x1, y1, x2, y2))
    return (_HEAD +
            '<circle cx="50" cy="50" r="42"/>'
            + "".join(ticks) +
            '<line x1="50" y1="50" x2="50" y2="26" stroke-width="5"/>'
            '<line x1="50" y1="50" x2="66" y2="58" stroke-width="5"/>'
            '<circle cx="50" cy="50" r="3.5" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _alert():
    """警示三角。"""
    return (_HEAD +
            '<path d="M50 12 L91 84 H9 Z"/>'
            '<line x1="50" y1="38" x2="50" y2="60" stroke-width="6"/>'
            '<circle cx="50" cy="71" r="3.6" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _target():
    """靶心（目标 / 命中语义）。"""
    return (_HEAD +
            '<circle cx="50" cy="50" r="42"/>'
            '<circle cx="50" cy="50" r="27" stroke-width="4"/>'
            '<circle cx="50" cy="50" r="12" stroke-width="4"/>'
            '<circle cx="50" cy="50" r="3.5" fill="{COLOR}" stroke="none"/>'
            '<line x1="50" y1="50" x2="86" y2="14" stroke-width="4"/>'
            '</svg>')


def _key():
    """钥匙（解锁 / 承认语义）。"""
    return (_HEAD +
            '<circle cx="34" cy="36" r="20"/>'
            '<line x1="48" y1="50" x2="84" y2="86" stroke-width="6"/>'
            '<line x1="70" y1="72" x2="80" y2="62" stroke-width="5"/>'
            '<line x1="78" y1="80" x2="88" y2="70" stroke-width="5"/>'
            '</svg>')


def _envelope():
    """信封 + 折线（未说出口的话 / 留言）。"""
    return (_HEAD +
            '<rect x="12" y="24" width="76" height="54" rx="6"/>'
            '<path d="M14 28 L50 56 L86 28" stroke-width="4"/>'
            '<circle cx="78" cy="24" r="9" fill="none" stroke-width="4"/>'
            '</svg>')


def _calendar():
    """日历 + 圈选日（那一天 / 结案日）。"""
    return (_HEAD +
            '<rect x="14" y="20" width="72" height="68" rx="6"/>'
            '<line x1="14" y1="38" x2="86" y2="38" stroke-width="4"/>'
            '<line x1="32" y1="12" x2="32" y2="28" stroke-width="5"/>'
            '<line x1="68" y1="12" x2="68" y2="28" stroke-width="5"/>'
            '<circle cx="50" cy="62" r="12" stroke-width="4"/>'
            '</svg>')


def _chart_bar():
    """柱状图 + 上升箭头（增长 / 指标）。"""
    return (_HEADF +
            '<line x1="14" y1="86" x2="88" y2="86" stroke-width="4" stroke-linecap="round"/>'
            '<rect x="22" y="58" width="12" height="28" stroke-width="3.5"/>'
            '<rect x="42" y="42" width="12" height="44" stroke-width="3.5"/>'
            '<rect x="62" y="26" width="12" height="60" stroke-width="3.5"/>'
            '<path d="M24 48 L48 30 L70 14" stroke-width="4" stroke-linecap="round"/>'
            '<path d="M70 14 L60 15 M70 14 L69 24" stroke-width="4" stroke-linecap="round"/>'
            '</svg>')


def _chart_line():
    """折线图 + 数据点（趋势 / 时间序列）。"""
    pts = [(16, 70), (34, 56), (50, 62), (66, 38), (84, 26)]
    poly = " ".join("%d,%d" % p for p in pts)
    dots = "".join('<circle cx="%d" cy="%d" r="3.4" fill="{COLOR}" stroke="none"/>' % p
                   for p in pts)
    return (_HEADF +
            '<line x1="12" y1="88" x2="88" y2="88" stroke-width="3.5" stroke-linecap="round"/>'
            '<polyline points="%s" stroke-width="4.5" stroke-linecap="round" '
            'stroke-linejoin="round"/>' % poly + dots + '</svg>')


def _progress_ring():
    """环形进度 + 百分比弧（完成度 / 等待）。"""
    a = math.radians(240)
    ex, ey = 50 + 34 * math.sin(a), 50 - 34 * math.cos(a)
    return (_HEAD +
            '<circle cx="50" cy="50" r="34" stroke-width="7" stroke-opacity="0.28"/>'
            '<path d="M50 16 A34 34 0 1 1 %.1f %.1f" stroke-width="7" '
            'stroke-linecap="round"/>' % (ex, ey) +
            '<circle cx="50" cy="50" r="7" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _flag():
    """旗帜立在杆上（立场 / 达成）。"""
    return (_HEAD +
            '<line x1="30" y1="10" x2="30" y2="90" stroke-width="5"/>'
            '<path d="M30 16 H78 L64 34 L78 52 H30 Z" stroke-width="4"/>'
            '<circle cx="30" cy="10" r="4" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _balance():
    """天平（权衡 / 公正）。"""
    return (_HEAD +
            '<line x1="50" y1="14" x2="50" y2="82" stroke-width="5"/>'
            '<line x1="20" y1="30" x2="80" y2="30" stroke-width="5"/>'
            '<path d="M20 30 L12 50 H28 Z" stroke-width="3.5"/>'
            '<path d="M80 30 L72 50 H88 Z" stroke-width="3.5"/>'
            '<line x1="34" y1="86" x2="66" y2="86" stroke-width="5"/>'
            '<circle cx="50" cy="30" r="4" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _bulb():
    """灯泡 + 光芒（想法 / 领悟）。"""
    rays = "".join('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="3"/>'
                   % (50 + 44 * math.sin(math.radians(d)),
                      50 - 44 * math.cos(math.radians(d)),
                      50 + 34 * math.sin(math.radians(d)),
                      50 - 34 * math.cos(math.radians(d)))
                   for d in (0, 45, 90, 135, 180, 225, 270, 315))
    return (_HEAD + rays +
            '<path d="M38 52 A12 12 0 1 1 62 52 C62 60 56 62 56 70 H44 '
            'C44 62 38 60 38 52 Z" stroke-width="4"/>'
            '<line x1="44" y1="78" x2="56" y2="78" stroke-width="4"/>'
            '<line x1="46" y1="86" x2="54" y2="86" stroke-width="4"/>'
            '</svg>')


def _bookmark():
    """书签（标记 / 记住）。"""
    return (_HEAD +
            '<path d="M30 8 H70 V90 L50 72 L30 90 Z" stroke-width="4.5"/>'
            '<circle cx="50" cy="34" r="6" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _lock():
    """挂锁（未结案 / 封存）。"""
    return (_HEAD +
            '<rect x="24" y="44" width="52" height="42" rx="6" stroke-width="4.5"/>'
            '<path d="M36 44 V32 A14 14 0 0 1 64 32 V44" stroke-width="4.5"/>'
            '<circle cx="50" cy="64" r="4.5" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _hourglass():
    """沙漏（时间只有一个方向）。"""
    return (_HEAD +
            '<line x1="26" y1="10" x2="74" y2="10" stroke-width="5"/>'
            '<line x1="26" y1="90" x2="74" y2="90" stroke-width="5"/>'
            '<path d="M30 12 C30 40 46 44 46 50 C46 56 30 60 30 88" stroke-width="4"/>'
            '<path d="M70 12 C70 40 54 44 54 50 C54 56 70 60 70 88" stroke-width="4"/>'
            '<path d="M40 80 H60 L50 66 Z" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _map_pin():
    """地图针 + 底层圈（坐标 / 立场）。"""
    return (_HEAD +
            '<path d="M50 8 C34 8 24 22 24 36 C24 56 50 88 50 88 '
            'C50 88 76 56 76 36 C76 22 66 8 50 8 Z" stroke-width="4.5"/>'
            '<circle cx="50" cy="36" r="9" stroke-width="4"/>'
            '</svg>')


def _gears():
    """齿轮 + 齿（运转 / 机制）。"""
    teeth = "".join('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="4"/>'
                    % (50 + 26 * math.sin(math.radians(d)),
                       50 - 26 * math.cos(math.radians(d)),
                       50 + 38 * math.sin(math.radians(d)),
                       50 - 38 * math.cos(math.radians(d)))
                    for d in range(0, 360, 45))
    return (_HEAD + teeth +
            '<circle cx="50" cy="50" r="26" stroke-width="5"/>'
            '<circle cx="50" cy="50" r="9" stroke-width="4"/>'
            '</svg>')


def _trophy():
    """奖杯（赢 / 承认）。"""
    return (_HEAD +
            '<path d="M32 12 H68 V40 A18 18 0 0 1 32 40 Z" stroke-width="4.5"/>'
            '<path d="M32 18 H20 V28 A12 12 0 0 0 32 40" stroke-width="3.5"/>'
            '<path d="M68 18 H80 V28 A12 12 0 0 1 68 40" stroke-width="3.5"/>'
            '<line x1="50" y1="58" x2="50" y2="76" stroke-width="5"/>'
            '<line x1="34" y1="86" x2="66" y2="86" stroke-width="5"/>'
            '</svg>')


def _compass():
    """罗盘（方向）。"""
    return (_HEAD +
            '<circle cx="50" cy="50" r="42"/>'
            '<path d="M50 22 L60 50 L50 78 L40 50 Z" stroke-width="4"/>'
            '<circle cx="50" cy="50" r="3.5" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _puzzle():
    """拼图块（缺失的一块 / 复原）。"""
    return (_HEAD +
            '<path d="M16 20 H46 V34 A8 8 0 1 0 62 34 V20 H84 V52 H70 '
            'A8 8 0 1 0 70 68 H84 V84 H16 Z" stroke-width="4.5"/>'
            '</svg>')


def _cumulative():
    """南丁格尔玫瑰式累积图（累计 / 叠加）。"""
    rings = "".join('<circle cx="50" cy="80" r="%d" stroke-width="3"/>' % r
                    for r in (12, 22, 32, 42, 52))
    return (_HEADF + rings +
            '<line x1="50" y1="80" x2="50" y2="16" stroke-width="3" stroke-linecap="round"/>'
            '<line x1="50" y1="80" x2="86" y2="80" stroke-width="3" stroke-linecap="round"/>'
            '</svg>')


# ---------------------------------------------------------------- decor

def _dot_grid():
    dots = "".join('<circle cx="%d" cy="%d" r="2.2" fill="{COLOR}" stroke="none"/>'
                   % (cx, cy)
                   for cx, cy in _lattice(5, 4, 10, 12, 20, 25))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            + dots + '</svg>')


def _ring_pair():
    """同心双环（实线 + 虚线）。"""
    return (_HEADF +
            '<circle cx="50" cy="50" r="47" stroke-width="1.8"/>'
            '<circle cx="50" cy="50" r="37" stroke-width="1.2" stroke-dasharray="3 5"/>'
            '</svg>')


def _tick_line():
    """刻度横线。"""
    ticks = "".join('<line x1="%d" y1="44" x2="%d" y2="56" stroke-width="2"/>'
                    % (x, x) for x in (20, 35, 50, 65, 80))
    return (_HEADF +
            '<line x1="4" y1="50" x2="96" y2="50" stroke-width="2.5" stroke-linecap="round"/>'
            + ticks + '</svg>')


def _divider():
    """居中竖向虚线。"""
    return (_HEADF +
            '<line x1="50" y1="4" x2="50" y2="96" stroke-width="2.5" '
            'stroke-dasharray="2 8" stroke-linecap="round"/>'
            '</svg>')


def _wave():
    """波纹线（情绪起伏 / 流动）。"""
    import math as _m
    pts = " ".join("%.1f,%.1f" % (i * 4.0, 50 + 16 * _m.sin(i * 0.6))
                   for i in range(0, 26))
    return (_HEADF +
            '<polyline points="%s" stroke-width="3" stroke-linecap="round" '
            'stroke-linejoin="round"/>' % pts + '</svg>')


def _scatter():
    """散点阵（数据 / 分布）。"""
    pts = [(18, 30), (30, 62), (42, 44), (54, 72), (66, 36), (78, 58),
           (26, 82), (70, 84), (88, 24), (14, 54)]
    dots = "".join('<circle cx="%d" cy="%d" r="2.6" fill="{COLOR}" stroke="none"/>' % p
                   for p in pts)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            + dots + '</svg>')


def _brackets():
    """方括号（聚焦 / 引用）。"""
    return (_HEADF +
            '<path d="M22 10 V90 H6 V20" stroke-width="3"/>'.replace('H6', 'H14') +
            '<path d="M78 10 V90 H86" stroke-width="3"/>'
            '</svg>')


def _halftone():
    """半调渐隐点阵（情绪衰减）。"""
    dots = "".join('<circle cx="%d" cy="%d" r="%.1f" fill="{COLOR}" stroke="none"/>'
                   % (cx, cy, 3.2 - 0.5 * (c + r))
                   for c, r, cx, cy in _lattice_idx(6, 5, 14, 20, 12, 14))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            + dots + '</svg>')


def _cross_hatch():
    """交叉网格（结构 / 底纹）。"""
    lines = []
    lo, hi = 4.0, 96.0
    # 两族 45° 斜线，裁剪到 [lo,hi]² 框内，绝不越 viewBox
    for c in range(-96, 97, 14):                      # x - y = c（斜率 +1）
        x0, x1 = max(lo, lo + c), min(hi, hi + c)
        if x0 < x1:
            lines.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="1.1"/>'
                         % (x0, x0 - c, x1, x1 - c))
    for c in range(8, 193, 14):                       # x + y = c（斜率 -1）
        x0, x1 = max(lo, c - hi), min(hi, c - lo)
        if x0 < x1:
            lines.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="1.1"/>'
                         % (x0, c - x0, x1, c - x1))
    return (_HEADF + "".join(lines) + '</svg>')


def _spiral():
    """螺旋（递归 / 循环）。"""
    pts = []
    for i in range(0, 80):
        a = i * 0.34
        r = 0.50 * i
        pts.append("%.1f,%.1f" % (50 + r * math.cos(a), 50 + r * math.sin(a)))
    return (_HEADF +
            '<polyline points="%s" stroke-width="2" fill="none" stroke-linecap="round"/>'
            % " ".join(pts) + '</svg>')


def _bar_mini():
    """迷你柱条（进度 / 对比底纹）。"""
    bars = "".join('<rect x="%d" y="%d" width="8" height="%d" stroke-width="2.4"/>'
                   % (16 + 14 * i, 88 - h, h)
                   for i, h in enumerate((20, 34, 26, 48, 40, 58)))
    return (_HEADF + bars + '</svg>')


def _ruler():
    """短标尺（度量 / 精确）。"""
    ticks = "".join('<line x1="%d" y1="40" x2="%d" y2="%d" stroke-width="2"/>'
                    % (x, x, 52 if (x // 10) % 2 else 46)
                    for x in range(14, 90, 6))
    return (_HEADF +
            '<line x1="8" y1="40" x2="92" y2="40" stroke-width="2.5" stroke-linecap="round"/>'
            + ticks + '</svg>')


def _plus_field():
    """加号阵（网格 / 体系）。"""
    plus = "".join('<path d="M%d %d h10 M%d %d v10" stroke-width="1.8"/>'
                   % (x - 5, y, x, y - 5)
                   for x, y in _lattice(3, 3, 22, 22, 28, 28))
    return (_HEADF + plus + '</svg>')


def _orbit():
    """轨道椭圆 + 点（关联 / 环绕）。"""
    return (_HEADF +
            '<ellipse cx="50" cy="50" rx="46" ry="22" stroke-width="1.8"/>'
            '<ellipse cx="50" cy="50" rx="22" ry="46" stroke-width="1.4" '
            'stroke-dasharray="3 5"/>'
            '<circle cx="96" cy="50" r="3" fill="{COLOR}" stroke="none"/>'
            '<circle cx="50" cy="4" r="2.4" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _arrow_chain():
    """箭头链（因果 / 递进）。"""
    arrow = ('<path d="M%d 50 H%d" stroke-width="2.6" stroke-linecap="round"/>'
             '<path d="M%d 45 L%d 50 L%d 55" stroke-width="2.6" fill="none" '
             'stroke-linecap="round" stroke-linejoin="round"/>')
    out = []
    for i, x in enumerate((12, 44, 76)):
        out.append(arrow % (x, x + 20, x + 20, x + 26, x + 20))
    return (_HEADF + "".join(out) + '</svg>')


def _milestone():
    """里程碑节点线（阶段 / 进度）。"""
    nodes = (16, 40, 64, 88)
    line = '<line x1="12" y1="50" x2="88" y2="50" stroke-width="2.4" stroke-linecap="round"/>'
    dots = "".join('<circle cx="%d" cy="50" r="%d" stroke-width="2" '
                   'fill="none"/>' % (x, 5 if i % 2 == 0 else 3)
                   for i, x in enumerate(nodes))
    return (_HEADF + line + dots + '</svg>')


def _corner_marks():
    """画框四角 L 形标记（保留兼容；v4.2.1 起默认不生成）。"""
    return (_HEADF +
            '<path d="M2 16 V2 H16" stroke-width="1.6"/>'
            '<path d="M84 2 H98 V16" stroke-width="1.6"/>'
            '<path d="M98 84 V98 H84" stroke-width="1.6"/>'
            '<path d="M16 98 H2 V84" stroke-width="1.6"/>'
            '</svg>')


ART = {
    # motifs
    "phone": _phone(), "moon": _moon(), "shield": _shield(),
    "clock": _clock(), "alert": _alert(), "target": _target(),
    "key": _key(), "envelope": _envelope(), "calendar": _calendar(),
    "chart_bar": _chart_bar(), "chart_line": _chart_line(),
    "progress_ring": _progress_ring(), "flag": _flag(), "balance": _balance(),
    "bulb": _bulb(), "bookmark": _bookmark(), "lock": _lock(),
    "hourglass": _hourglass(), "map_pin": _map_pin(), "gears": _gears(),
    "trophy": _trophy(), "compass": _compass(), "puzzle": _puzzle(),
    "cumulative": _cumulative(),
    # decor
    "dot_grid": _dot_grid(), "ring_pair": _ring_pair(),
    "tick_line": _tick_line(), "divider": _divider(), "wave": _wave(),
    "scatter": _scatter(), "brackets": _brackets(), "halftone": _halftone(),
    "cross_hatch": _cross_hatch(), "spiral": _spiral(), "bar_mini": _bar_mini(),
    "ruler": _ruler(), "plus_field": _plus_field(), "orbit": _orbit(),
    "arrow_chain": _arrow_chain(), "milestone": _milestone(),
    "corner_marks": _corner_marks(),
}

MOTIF_ARTS = (
    "phone", "moon", "shield", "clock", "alert", "target", "key", "envelope",
    "calendar", "chart_bar", "chart_line", "progress_ring", "flag", "balance",
    "bulb", "bookmark", "lock", "hourglass", "map_pin", "gears", "trophy",
    "compass", "puzzle", "cumulative",
)

DECOR_ARTS = (
    "dot_grid", "ring_pair", "tick_line", "divider", "wave", "scatter",
    "brackets", "halftone", "cross_hatch", "spiral", "bar_mini", "ruler",
    "plus_field", "orbit", "arrow_chain", "milestone",
)


# ---------------------------------------------------------------- gates

_NUM = re.compile(r"-?\d+\.?\d*")


def audit_svg(svg):
    """越界审计：所有坐标数必须落在 viewBox [-6, 106]（留 6% 笔锋余量）。

    返回 issues 列表；空列表 = PASS。这是机器门禁，画法越界会在
    self_test 中被拦下，而不是等渲染后才发现「图形缺一块」。
    """
    issues = []
    clean = re.sub(r"#[0-9A-Fa-f]{6}", "", svg)
    clean = clean.replace("http://www.w3.org/2000/svg", "")  # 命名空间 URL 非坐标
    for m in _NUM.finditer(clean):
        v = float(m.group(0))
        if v < -6 or v > VIEWBOX + 6:
            issues.append("coordinate %.1f outside viewBox" % v)
    return issues


def audit_all():
    bad = {name: audit_svg(svg) for name, svg in ART.items()}
    return {k: v for k, v in bad.items() if v}


@functools.lru_cache(maxsize=512)
def render_png(art, color, w, h):
    """cairosvg 光栅化为 RGBA PIL Image（带 LRU 缓存，视频渲染友好）。"""
    svg = ART[art].replace("{COLOR}", color)
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                           output_width=max(1, int(w)),
                           output_height=max(1, int(h)))
    return Image.open(io.BytesIO(png)).convert("RGBA")


# ---- v6.0 参考图（教科书信息图）新增装饰语汇 ----

def _conn_nodes():
    """三节点连线（流程 / 因果 / 传导）：盒装节点 + 连线 + 中继点。"""
    xs = (8, 40, 72)
    out = []
    for i, x in enumerate(xs):
        out.append('<rect x="%d" y="38" width="20" height="24" rx="4" stroke-width="2"/>' % x)
        if i < 2:
            nx = xs[i + 1]
            out.append('<line x1="%d" y1="50" x2="%d" y2="50" stroke-width="2"/>' % (x + 20, nx))
            out.append('<circle cx="%d" cy="50" r="2.2" fill="{COLOR}" stroke="none"/>'
                       % ((x + 20 + nx) / 2))
    return (_HEADF + "".join(out) + '</svg>')


def _mini_curve():
    """迷你曲线 + 坐标轴（增长 / 衰减 / 对数增速）。"""
    return (_HEADF +
            '<path d="M10 88 L10 12" stroke-width="1.8"/>'
            '<path d="M10 88 L92 88" stroke-width="1.8"/>'
            '<line x1="12" y1="70" x2="90" y2="70" stroke-width="1" stroke-dasharray="3 4"/>'
            '<path d="M12 82 C40 62 70 30 90 18" stroke-width="2.8" stroke-linecap="round"/>'
            '<circle cx="90" cy="18" r="2.6" fill="{COLOR}" stroke="none"/>'
            '</svg>')


def _chip_row():
    """盒装标签行（类别 / 选项 / 并列项）。"""
    out = []
    for x, w in ((6, 24), (36, 26), (68, 22)):
        out.append('<rect x="%d" y="42" width="%d" height="16" rx="6" stroke-width="1.8"/>'
                   % (x, w))
    return (_HEADF + "".join(out) + '</svg>')


ART["conn_nodes"] = _conn_nodes()
ART["mini_curve"] = _mini_curve()
ART["chip_row"] = _chip_row()
DECOR_ARTS = tuple(DECOR_ARTS) + ("conn_nodes", "mini_curve", "chip_row")
print("svg_art v6.0 decor added:", ART["conn_nodes"][:20], "ok")
