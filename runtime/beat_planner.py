"""Stage 1 — Beat baseline planner (v4.3 语义驱动).

v4.3 之前是纯时长贪心：攒够 2.5s 就切、8s 强制切。用户反馈「断句断得
很生涩完全没有逻辑」——根因是切刀完全不看文本语义，会把问答对
（「你要的到底是什么」→「你说是赢」）、让步对（铺垫→「可…」）、因果对
（陈述→「所以…」）从中间撕开。

v4.3 起，semantic_grouper 先做语义检索，产出分拍约束：

- 硬约束（keep_with_next）：answer_to / concession / conclusion 对内的
  每一对相邻 cue 都不得切开——这些对是一个完整的语义事件；
- 软约束（prefer_with_next）：echo（蝉联词组）/ ref_chain（指代回指）
  在 3 句以内优先同拍，但前瞻下一句——若并入后总时长会突破 MAX_D，
  则不延续（防止软约束粘连制造超长拍）；
- 绝对上限 HARD_CEIL = MAX_D × 1.75 = 14s：硬约束组可以超过 MAX_D
  （问答/让步对是一个完整语义事件，值得 10-13s 停留），但不许无限膨胀；
- 无语义约束的位置仍按原有时长规则落刀（MIN_D..MAX_D）。

时长规则（不变）：单拍短于 2.5s 观众读不完；长于 8s 无变化即「有声 PPT」；
硬约束组可放宽到 14s，但仍需入场编排层的节奏预算填补（skills/07）。
"""
import re

import semantic_grouper

MIN_D = 2.5
MAX_D = 8.0

_ROLE_HINTS = [
    ("hook", ("有没有", "想象", "有没有过", "如果")),
    ("emphasis", ("最关键", "最重要的是", "核心", "真正")),
    ("comparison", ("但是", "vs", "对比", "相比", "另一方面")),
    ("conclusion", ("所以", "因此", "总结", "结论", "换言之")),
]


def guess_role(text):
    for role, hints in _ROLE_HINTS:
        if any(h in text for h in hints):
            return role
    return "explanation"


def _join_texts(pieces):
    """把同一拍内的多条字幕拼成可读文本。

    旧实现用字符串直接相连（"".join），导致上一句结尾与下一句开头粘在一起
    （如「半点不由人」+「说这句话的人」→「半点不由人说这句话的人」）。
    这里在缺少标点处补一个逗号，保证断句合理。
    """
    PUNCT = "，。！？、；：,.!?;:…—）)」』】"
    out = ""
    for p in pieces:
        t = (p or "").strip()
        if not t:
            continue
        if out and out[-1] not in PUNCT:
            out += "，"
        out += t
    return out


def plan_beats(cues):
    """语义约束驱动的分拍。

    返回的每拍附带：
    - ``semantic_pairs``：拍内语义关系对（供导演层选策略/做透明化审计）；
    - ``out_relations``：跨拍语义关系（问拍→答拍等，供交接设计参考）。
    """
    cons = semantic_grouper.grouping_constraints(cues)
    keep = cons["keep_with_next"]       # 硬：i 与 i+1 必须同拍
    prefer = cons["prefer_with_next"]   # 软：时长允许时优先同拍
    hard_ceil = MAX_D * 1.75            # 硬约束组的绝对上限（14s）

    beats = []
    buf = []

    def close(buf):
        txt = _join_texts([c["text"] for c in buf])
        beats.append({
            "beat_id": "beat_%02d" % (len(beats) + 1),
            "cue_range": [buf[0]["id"], buf[-1]["id"]],
            "start_sec": buf[0]["start"], "end_sec": buf[-1]["end"],
            "duration_sec": round(buf[-1]["end"] - buf[0]["start"], 3),
            "narration": txt, "semantic_role": guess_role(txt),
            "motion_policy": "required",
        })

    for i, cue in enumerate(cues):
        buf.append(cue)
        dur = buf[-1]["end"] - buf[0]["start"]
        hard_locked = i in keep and i + 1 < len(cues)
        # 绝对上限：硬约束组也不得超过 HARD_CEIL（防止超长死拍）
        if dur >= (hard_ceil if hard_locked else MAX_D):
            close(buf)
            buf = []
            continue
        if dur >= MIN_D:
            # 语义硬约束：当前尾句与下一句不得拆开
            if hard_locked:
                continue
            # 数字与单位不得拆开（v4.0 规则保留）
            tail = cue["text"].rstrip("。，,.!！?？ ")
            if re.search(r"\d$", tail) and i + 1 < len(cues):
                continue
            # 语义软约束：优先延续同拍，但前瞻下一句——若并入后总时长
            # 会突破 MAX_D，则不延续（防止软约束粘连制造出超长拍，
            # 把硬约束组顶破 HARD_CEIL）
            if i in prefer and dur < MAX_D and i + 1 < len(cues):
                if cues[i + 1]["end"] - buf[0]["start"] <= MAX_D:
                    continue
            close(buf)
            buf = []
    if buf:
        close(buf)

    # 过短的尾巴并入前一拍（避免 1s 孤拍）
    if len(beats) >= 2 and beats[-1]["duration_sec"] < 1.2:
        last = beats.pop()
        prev = beats[-1]
        merged = dict(prev)
        merged["cue_range"] = [prev["cue_range"][0], last["cue_range"][1]]
        merged["end_sec"] = last["end_sec"]
        merged["duration_sec"] = round(
            last["end_sec"] - prev["start_sec"], 3)
        merged["narration"] = _join_texts([prev["narration"], last["narration"]])
        merged["semantic_role"] = guess_role(merged["narration"])
        beats[-1] = merged

    # ---- 语义关系落位：cue 位置 → 拍 ----
    pairs, _ = semantic_grouper.find_pairs(cues)
    id2pos = {c["id"]: k for k, c in enumerate(cues)}
    pos2beat = {}
    for bi, b in enumerate(beats):
        for pos in range(id2pos[b["cue_range"][0]],
                         id2pos[b["cue_range"][1]] + 1):
            pos2beat[pos] = bi
    for b in beats:
        b["semantic_pairs"] = []
        b["out_relations"] = []
    for p in pairs:
        a, bto = p["from"], p["to"]
        ba, bb = pos2beat.get(a), pos2beat.get(bto)
        if ba is None or bb is None:
            continue
        entry = dict(p)
        entry["from_cue"] = cues[a]["id"]
        entry["to_cue"] = cues[bto]["id"]
        if ba == bb:
            beats[ba]["semantic_pairs"].append(entry)
        else:
            beats[ba]["out_relations"].append(
                {"type": p["type"], "to_beat": beats[bb]["beat_id"],
                 "to_cue": entry["to_cue"]})
    return beats
