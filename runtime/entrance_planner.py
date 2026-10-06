"""入场编排（entrance plan）—— 薄委托层（P0 Production Path Canonical 收敛）。

历史：本模块曾自带第四套运动词汇与完整入场算法（``PHASES`` / ``_WAVE`` /
``_build_lifecycle`` / ``plan`` / ``audit``）。这造成 legacy producer 与
canonical producer **同时承担生产职责**。为消除该双生产，算法已收敛到唯一实现
:mod:`motion_canonical.entrance`；本模块只保留：

1. **部署契约所固定的 motion 词表**（供 docs / 只读外部消费者引用）；
2. 向后兼容别名（``PHASES`` / ``_WAVE`` / ``_EXIT_MOTION`` / ``MOTIONS_*`` /
   ``_group_of`` / ``_build_lifecycle`` / ``_cues_from_lifecycle`` / ``_respace_cues`` /
   ``_interactions``）；
3. ``plan`` / ``audit`` 直接委托 canonical。

契约不变量（``schemas/entrance-plan.schema.json`` + ``html_adapter`` / ``raster_renderer``）::

    enter motion ∈ ("fade", "rise", "pop", "inherit")
    exit  motion ∈ ("fade", "sink", "shrink")

canonical 版必须序列化这些 **部署 token**，而非 canonical action 名
（``carry_over`` / ``fade_out``）；否则 schema 校验失败、渲染器无法识别、并破坏
``tests/test_golden.py`` 的 ``entrance-plan.json`` 哈希。该对齐已由
``tests/phase0/test_production_canonical_boundary.py`` 机器校验。

相隔波次间隔：生产固定为 ``common.G_MIN_WAVE_GAP``（0.25s），与 canonical 默认值
（0.35s）不同，因此委托时显式转发，以保持输出与历史生产字节级一致。
"""
from common import G_MIN_WAVE_GAP

from motion_canonical import entrance as _canon
from motion_canonical.entrance import (
    PHASES,
    DEFAULT_MIN_WAVE_GAP,
    group_of as _group_of,
    build_lifecycle as _build_lifecycle,
    cues_from_lifecycle as _cues_from_lifecycle,
    interactions as _interactions,
)

# --- 部署契约词表（只读；motion-inventory / 外部消费者引用） ----------------------
MOTIONS_ENTER = ("fade", "rise", "pop", "inherit")
MOTIONS_EXIT = ("fade", "sink", "shrink")

# 波次锚点 / 退场选择：直接引用 canonical 的唯一表，避免二次 fork。
_WAVE = _canon._WAVE
_EXIT_MOTION = _canon._EXIT_MOTION


def _respace_cues(cues, life, start, dur, min_gap=None):
    """向后兼容别名：委托 canonical，并保持 G_MIN_WAVE_GAP 默认。"""
    return _canon.respace_cues(
        cues, life, start, dur, G_MIN_WAVE_GAP if min_gap is None else min_gap)


def plan(dsl, min_gap=None):
    """dsl → entrance plan。委托 :mod:`motion_canonical.entrance`（唯一生产实现）。"""
    return _canon.plan(dsl, G_MIN_WAVE_GAP if min_gap is None else min_gap)


def audit(entrance, min_gap=None):
    """entrance plan → G1..G5 门禁（含 lifecycle 完整性）。委托 canonical。"""
    return _canon.audit(entrance, G_MIN_WAVE_GAP if min_gap is None else min_gap)
