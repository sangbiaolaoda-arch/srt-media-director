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
    assert "visual_grammar.composition_strategy(" in src
    assert 'SEMANTIC_DEFAULT.get(' not in src


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
