"""runtime/motion_runtime/identity.py — 稳定对象身份（Runtime Hardening · P1）。

每个视觉对象必须拥有稳定 ID（person_01 / choice_03 / cause_01 ...）。
对象只是移动 / 缩放 / 变形时 **保留 ID**；不得 destroy-old / create-new，
除非语义明确要求 split / merge / transform / replace。

这是保证视觉连续性的基础，也是 Identity invariant 的机器可验证对象。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# 只有这些语义运动被允许改变对象身份
ID_CHANGING = ("SPLIT", "MERGE", "MORPH", "TRANSFORM", "REPLACE")

# 索引（child → 来源）在 split/merge 后建立「血缘」，保证可追溯
@dataclass
class Lineage:
    child: str
    source: str
    via: str  # the motion_type that caused it


class IdentityRegistry:
    """记录并校验对象身份的连续性。"""

    def __init__(self):
        self._ids: Set[str] = set()
        self._lineage: List[Lineage] = []

    def register(self, nid: str) -> None:
        self._ids.add(nid)

    def register_all(self, ids) -> None:
        for i in ids:
            self._ids.add(i)

    def known(self, nid: str) -> bool:
        return nid in self._ids

    def record_lineage(self, child: str, source: str, via: str) -> None:
        self._lineage.append(Lineage(child, source, via))
        self._ids.add(child)

    @property
    def lineage(self) -> List[Lineage]:
        return list(self._lineage)

    @staticmethod
    def preserves_identity(motion_type: str) -> bool:
        return motion_type not in ID_CHANGING


def check_identity_continuity(before_ids: List[str], after_ids: List[str],
                              motions) -> List[str]:
    """普通 transition 中 id 不能改变。

    规则：若本次所有 motion 都是「保身份」的，则 before_ids 必须等于 after_ids。
    返回违规说明列表（空 = 通过）。
    """
    violations: List[str] = []
    changing = [m for m in motions
                if not IdentityRegistry.preserves_identity(
                    m.motion_type if hasattr(m, "motion_type") else str(m))]
    if not changing:
        missing = set(before_ids) - set(after_ids)
        added = set(after_ids) - set(before_ids)
        if missing:
            violations.append("identity lost for %s without split/merge/transform"
                              % sorted(missing))
        if added:
            violations.append("identity created for %s without explicit semantic"
                              % sorted(added))
    return violations
