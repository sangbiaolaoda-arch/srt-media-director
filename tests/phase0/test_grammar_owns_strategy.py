"""P2 — Visual Grammar 接管 Director：构图策略决策权收敛门禁。

证明：构图策略（一个拍子用哪种视觉构图模板）的决策词汇现在由
:mod:`visual_grammar` 层唯一拥有，``visual_director`` 只是消费者；且该收敛
**行为保持**（与收敛前逐字节等价）。

  1. 源码：``visual_director`` 不再自带策略决策表；
  2. 路由：``_direct_beat`` 通过 ``visual_grammar.composition_strategy`` 决策；
  3. 等价：对覆盖全部分支的 (encoding, role, semantic_pairs) 组合，
     ``visual_grammar.composition_strategy`` 与收敛前的嵌入参考逻辑逐一相等；
  4. 值域：产出策略 ∈ ``visual_director.STRATEGIES``。
"""
import ast
import inspect
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import visual_director  # noqa: E402
import visual_grammar  # noqa: E402


def _old_strategy(beat, encoding):
    """收敛前 visual_director._direct_beat 的策略决策（嵌入参考实现）。"""
    if encoding["type"] == "part_to_whole":
        return "center_cluster"
    if encoding["type"] == "change_over_time":
        return "before_after"
    if encoding["type"] == "semantic_color_pair" or \
            beat["semantic_role"] == "comparison":
        return "comparison"
    pairs = beat.get("semantic_pairs", [])
    if any(p["type"] in ("answer_to", "conclusion") for p in pairs):
        return "cause_effect"
    if any(p["type"] == "concession" for p in pairs):
        return "comparison"
    rd = visual_director.SEMANTIC_DEFAULT.get(beat["semantic_role"], "single_focus")
    return rd if rd != "single_focus" else "single_focus"


def test_director_no_longer_owns_strategy_table():
    src = inspect.getsource(visual_director)
    assert "SEMANTIC_DEFAULT = {" not in src, "director still defines the strategy table"
    assert visual_director.SEMANTIC_DEFAULT is visual_grammar.SEMANTIC_DEFAULT


def test_direct_beat_routes_through_grammar():
    src = inspect.getsource(visual_director._direct_beat)
    # P2-1：Director 消费 Grammar 的**候选集**（决策词汇仍在 Grammar）。
    assert "visual_grammar.composition_candidates(" in src
    assert 'SEMANTIC_DEFAULT.get(' not in src


def test_grammar_owns_composition_candidates():
    """P2-1：Grammar 拥有多候选；首候选恒等于向后兼容的单值决策；候选∈STRATEGIES。"""
    combos = [
        ({}, {"type": "none"}),
        ({"semantic_role": "hook"}, {"type": "none"}),
        ({"semantic_role": "emphasis"}, {"type": "none"}),
        ({"semantic_role": "explanation"}, {"type": "none"}),
        ({"semantic_role": "explanation"},
         {"type": "part_to_whole"}),
        ({"semantic_role": "explanation", "semantic_pairs": [{"type": "answer_to"}]},
         {"type": "none"}),
        ({"semantic_role": "explanation", "semantic_pairs": [{"type": "concession"}]},
         {"type": "none"}),
    ]
    for beat, encoding in combos:
        cands = visual_grammar.composition_candidates(beat, encoding)
        assert len(cands) >= 2, (beat, encoding, cands)
        assert cands[0]["strategy"] == visual_grammar.composition_strategy(beat, encoding)
        assert all(c["strategy"] in visual_director.STRATEGIES for c in cands)
        fits = [c["semantic_fit"] for c in cands]
        assert fits == sorted(fits, reverse=True)
        acc = visual_grammar.acceptable_candidates(beat, encoding)
        assert len(acc) >= 2 and acc[0]["strategy"] == cands[0]["strategy"]


def test_director_uses_decision_record():
    """P2-1：每拍产出可解释构图决策记录（候选集 + 选择 + 依据）。"""
    src = inspect.getsource(visual_director)
    assert "composition_decision" in src
    assert "_select_strategy" in src
    # R8 由「固定 ROTATION 硬轮换」升级为「候选集内软偏好」。
    body = inspect.getsource(visual_director._direct_beat)
    assert "ROTATION" not in body


CASES = [
    ({"type": "part_to_whole"}, "explanation", [], "center_cluster"),
    ({"type": "change_over_time"}, "hook", [], "before_after"),
    ({"type": "semantic_color_pair"}, "explanation", [], "comparison"),
    ({"type": "none"}, "comparison", [], "comparison"),
    ({"type": "none"}, "hook", [], "left_to_right_flow"),
    ({"type": "none"}, "emphasis", [], "center_cluster"),
    ({"type": "none"}, "explanation", [{"type": "answer_to"}], "cause_effect"),
    ({"type": "none"}, "explanation", [{"type": "conclusion"}], "cause_effect"),
    ({"type": "none"}, "explanation", [{"type": "concession"}], "comparison"),
    ({"type": "none"}, "explanation",
     [{"type": "answer_to"}, {"type": "concession"}], "cause_effect"),
    ({"type": "none"}, "explanation", [], "single_focus"),
    ({"type": "none"}, "turning_point", [], "single_focus"),
    ({"type": "none"}, "conclusion", [], "single_focus"),
]


@pytest.mark.parametrize("encoding,role,pairs,want", CASES)
def test_strategy_matches_deployed_logic(encoding, role, pairs, want):
    beat = {"semantic_role": role, "semantic_pairs": pairs}
    got = visual_grammar.composition_strategy(beat, encoding)
    assert got == want
    assert got == _old_strategy(beat, encoding)
    assert got in visual_director.STRATEGIES
