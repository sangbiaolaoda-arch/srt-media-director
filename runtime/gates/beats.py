"""Beat planning / semantic grouping gates."""
import json  # noqa: F401
import os  # noqa: F401
import shutil  # noqa: F401
import sys  # noqa: F401
import tempfile  # noqa: F401

from gate_lib import (  # noqa: F401
    GATES, gate, RUNTIME, ROOT, EXAMPLE_SRT, EXAMPLE_OVERRIDES,
    _example_beats, _example_dsl, pytest_approx,
    _MOTION_TRUTH_DIRS, _EASE_FINGERPRINTS, _MAT_FINGERPRINTS,
)

import beat_planner  # noqa: F401
import composition_planner  # noqa: F401
import entrance_planner  # noqa: F401
import html_adapter  # noqa: F401
import pipeline  # noqa: F401
import raster_renderer  # noqa: F401
import srt_parser  # noqa: F401
import svg_art  # noqa: F401
import visual_director  # noqa: F401


@gate("2. Beat 基线（不丢字幕 / 不拆语义单位）")
def g2():
    a, beats = _example_beats()
    assert 4 <= len(beats) <= 10, len(beats)
    covered = []
    for b in beats:
        covered.extend(range(b["cue_range"][0], b["cue_range"][1] + 1))
    assert covered == list(range(1, 9)), covered
    assert "".join(b["narration"] for b in beats) == "".join(
        c["text"] for c in a["cues"])
    # v4.3 语义检索：问答/让步/因果对必须同拍（硬约束不得被切开）
    synth = [{"id": i + 1, "start": i * 2.0, "end": i * 2.0 + 1.8, "text": t}
             for i, t in enumerate([
                 "你这么拼到底是想赢给谁看",          # 1 问句
                 "你大概会说你是为了自己",            # 2 答句（紧随问句）
                 "你真的很拼很努力每一天",            # 3 铺垫
                 "可它总会在某个晚上回来",            # 4 转折（让步）
                 "时间只有一个方向不可逆",            # 5 陈述
                 "所以你要的到底是什么",              # 6 结论（因果）
                 "签字那一刻你等了很久",              # 7
                 "那个字也可以自己签",                # 8
             ])]
    sb = beat_planner.plan_beats(synth)

    def _bid(cid):
        return next(b["beat_id"] for b in sb
                    if b["cue_range"][0] <= cid <= b["cue_range"][1])
    assert _bid(1) == _bid(2), sb      # 问答硬约束：问句与答句同拍
    assert _bid(3) == _bid(4), sb      # 让步硬约束：铺垫与转折同拍
    assert _bid(5) == _bid(6), sb      # 因果硬约束：陈述与所以同拍
    assert any(p["type"] == "answer_to"
               for b in sb for p in b["semantic_pairs"]), \
        [b["semantic_pairs"] for b in sb]
    assert all(b["duration_sec"] <= beat_planner.MAX_D * 1.75 + 0.01
               for b in sb), [b["duration_sec"] for b in sb]  # 硬约束组也不许超长


@gate("11. 语义断句（同拍拼接不粘连 / 硬约束不可拆）")
def g11():
    # 无标点拼接必须补逗号，禁止两句话首尾粘连
    j = beat_planner._join_texts(["万般皆是命，半点不由人", "说这句话的人", "其实很努力"])
    assert "人说这句话的人" not in j, j
    assert "，" in j, j
    a, beats = _example_beats()
    assert "".join(b["narration"] for b in beats) == "".join(
        c["text"] for c in a["cues"]).replace("\n", "")
    # 每拍 narration 内部不应出现「句号/问号/感叹号 + 无标点直接接字」
    for b in beats:
        n = b["narration"]
        assert "。说" not in n and "？说" not in n, (b["beat_id"], n)
