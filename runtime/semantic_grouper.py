"""Stage 1.5 — Semantic retrieval for beat grouping (v4.3).

用户反馈：「断句断得很生涩完全没有逻辑」。根因是纯时长贪心会把语义对
（问答、铺垫-转折、原因-结论、蝉联重复）从中间切开。

本模块在切拍**之前**做轻量中文语义检索，产出两类供下游使用的结构：

- ``pairs`` 语义关系对 ``[{"type", "from", "to"}]``（cue 下标，from<to）：
    - ``answer_to``  问答对（问句 → 后续短答/结论句）
    - ``concession`` 让步对（铺垫句 → 「可/但/却…」转折句）
    - ``conclusion`` 因果对（陈述 → 「所以/因为/正因如此…」句）
    - ``echo``       蝉联对（≥2 字内容词组在 ±4 句内复现）
    - ``ref_chain``  指代链（那件事/那句话/那个人/这一天/他/它 的延续）
- ``beat_relations`` 跨拍语义关系（from=尾 cue, to=首 cue）：
    - ``reveals``    问拍 → 答拍（visual_director 画揭示箭头）
    - ``contrasts``  铺垫拍 → 转折拍

检测是规则式的（无外部模型依赖），只作分拍与视觉布局的**约束**，
不改写任何旁白原文（CORE-02）。
"""
import re

# 标点与停用字符（分词用：中文按字/词组切片，不引入分词库）
_PUNCT = re.compile(r"[，。！？；：、,.!?;:\"'“”‘’…—\-\s]+")

# 问句判定：显式问词/问号结尾
_QUESTION_MARKS = ("吗", "呢", "什么", "为什么", "哪", "谁", "？", "?",
                   "到底", "到底是", "有没有")
# 转折标记（铺垫 → 转折）
_TURN = ("可", "可是", "但", "但是", "然而", "却", "其实", "只不过")
# 结论/因果标记
_CONCL = ("所以", "因此", "于是", "正因如此", "这就是为什么", "因为")
# 指代延续（承上启下的回指词）
_REF = ("那件事", "那句话", "那个人", "那一天", "这一天", "那句", "那件")


def _norm(text):
    return _PUNCT.sub("", text)


def _is_question(text):
    t = text.strip()
    if t.endswith(("？", "?")):
        return True
    return any(m in t for m in _QUESTION_MARKS)


def _starts_with(text, words):
    return any(text.startswith(w) for w in words)


def _has(text, words):
    return any(w in text for w in words)


def _content_ngrams(text, n=(2, 3, 4)):
    """抽取内容 n-gram（去标点后按 2-4 字滑动），用于蝉联检测。"""
    t = _norm(text)
    grams = set()
    for k in n:
        for i in range(0, max(0, len(t) - k + 1)):
            grams.add(t[i:i + k])
    return grams


def find_pairs(cues, max_span=6):
    """对 cue 序列做语义检索，返回 (pairs, beat_relations)。"""
    texts = [c["text"] for c in cues]
    n = len(texts)
    q_idx = [i for i, t in enumerate(texts) if _is_question(t)]

    pairs, rels = [], []

    # 1) 问答对：问句 → 其后 1-3 句内的首个短答/非问句
    for qi in q_idx:
        for j in range(qi + 1, min(n, qi + 4)):
            if not _is_question(texts[j]):
                pairs.append({"type": "answer_to", "from": qi, "to": j})
                if j > qi + 1:  # 跨拍问答 → 视觉揭示关系
                    rels.append({"type": "reveals", "from": qi, "to": j})
                break

    # 2) 让步对：铺垫句 → 转折句（转折标记出现在句首或紧随短句）
    for i in range(n - 1):
        t2 = texts[i + 1].strip()
        if _starts_with(t2, _TURN) or ("，" in t2 and _has(t2.split("，")[1], _TURN)):
            pairs.append({"type": "concession", "from": i, "to": i + 1})
            rels.append({"type": "contrasts", "from": i, "to": i + 1})

    # 3) 因果对：陈述 → 「所以/因为…」结论句
    for i in range(n - 1):
        t2 = texts[i + 1].strip()
        if _starts_with(t2, _CONCL):
            pairs.append({"type": "conclusion", "from": i, "to": i + 1})

    # 4) 指代链：含回指词的句子与其上文（±max_span 内）
    for i, t in enumerate(texts):
        if _has(t, _REF):
            for j in range(max(0, i - max_span), i):
                pairs.append({"type": "ref_chain", "from": j, "to": i})
                break  # 只链最近的一个上文锚点

    # 5) 蝉联对：内容 n-gram 在 ±4 句内复现（如「排练」「签字」「结案」）
    grams = [_content_ngrams(t) for t in texts]
    for i in range(n):
        for j in range(i + 1, min(n, i + 5)):
            common = grams[i] & grams[j]
            strong = [g for g in common if len(g) >= 2
                      and g not in ("的是", "你了", "我在", "他在")]
            if strong:
                # 确定性锚点：长度并列时再按字典序，避免集合迭代序
                # （受 PYTHONHASHSEED 影响）泄漏到产物，破坏跨进程可复现。
                anchor = sorted(strong, key=lambda g: (len(g), g))[-1]
                pairs.append({"type": "echo", "from": i, "to": j,
                              "anchor": anchor})

    return pairs, rels


# ---- 分拍约束视角 -----------------------------------------------------------

# 硬约束：这些关系对不得被切开（必须同拍）
_HARD = {"answer_to", "concession", "conclusion"}
# 软约束：尽量同拍（2-3 句内优先），但允许被时长/容量强制拆开
_SOFT = {"echo", "ref_chain"}


def grouping_constraints(cues):
    """把语义检索结果编译成分拍约束。

    返回 ``{"keep_with_next": set(i), "prefer_with_next": set(i)}``，
    下标 i 表示「第 i 句应与第 i+1 句同拍」。
    """
    pairs, _ = find_pairs(cues)
    keep, prefer = set(), set()
    for p in pairs:
        a, b = p["from"], p["to"]
        if p["type"] in _HARD:
            for k in range(a, b):        # 对内的每一对相邻 cue 都锁住
                keep.add(k)
        elif p["type"] in _SOFT and b - a <= 3:
            for k in range(a, b):
                prefer.add(k)
    return {"keep_with_next": keep, "prefer_with_next": prefer}


def cross_beat_relations(cues):
    """跨拍语义关系（供 visual_director 画揭示/对照箭头）。"""
    _, rels = find_pairs(cues)
    return rels
