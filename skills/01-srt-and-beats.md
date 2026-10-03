# 01 · SRT 解析与 Beat 切分

> 阶段产物：`work/srt-analysis.json` → `work/beat-plan.json`
> 参考实现：`runtime/srt_parser.py` · `runtime/beat_planner.py`
> 上游约束：`00-core-contract.md` CORE-01 / CORE-02

## 1. SRT 是唯一时间真值

- **SRT-01 [强制]** 正式时间轴只来自 SRT 时间码。禁止按字数、语速重新
  估算；禁止在下游层「微调」某拍的起止时间来迁就动画。
- **SRT-02 [强制]** 解析失败要显式报告，不得静默跳过。必须检测并输出：
  - `SRT_NO_TIME`：块内找不到时间行；
  - `SRT_INVERTED`：end ≤ start；
  - `SRT_OVERLAP`：后一条 start < 前一条 end（重叠字幕会破坏拍切分）。
- **SRT-03 [经验]** 解析同时产出**表层特征**（不产生新事实）：
  `numbers`（数字及其所在 cue，供信息编码层用）、`gaps`（相邻 cue 间的
  静音间隙，供节奏层用）。

`srt-analysis.json` 契约（schema 见 `schemas/srt-analysis.schema.json`）：

```json
{
  "timing_source": "srt",
  "total_duration_sec": 38.0,
  "cues": [{"id": 1, "start": 0.0, "end": 3.5, "text": "……"}],
  "numbers": [{"cue_id": 5, "span": "20%"}],
  "gaps": [],
  "errors": []
}
```

## 2. Beat：最小导演单位

一个 Beat 是时间上连续、语义上完整、拥有明确视觉变化的最小单位。
「机切」只产出基线，语义复核由 Agent 完成（可用
`examples/minimal/director_overrides.json` 的形式人工介入）。

- **BEAT-01 [强制]** 不丢字幕：每条 cue 恰好属于一个 beat；全部 beat 的
  cue 覆盖必须等于 `1..N`（机器可校验，见 `09-validation-repair.md` L1）。
- **BEAT-02 [强制]** 不把数字和单位拆开：cue 以数字结尾且后面还有内容时，
  继续并入下一 cue，直到语义单位闭合。
- **BEAT-02b [强制]** 不拆语义对（v4.3 语义检索）：切拍前先做轻量中文语义检索
  （`runtime/semantic_grouper.py`），产出分拍约束：
  - **硬约束**（不得切开）：`answer_to` 问答对、`concession` 让步对
    （铺垫→「可/但/却…」）、`conclusion` 因果对（陈述→「所以/因为…」）。
    这些对是一个完整语义事件，从中间撕开就是「断句生涩」的根因。
  - **软约束**（优先同拍）：`echo` 蝉联对（≥2 字词组在 ±4 句内复现）、
    `ref_chain` 指代链（那件事/那句话…）；前瞻下一句，若并入后总时长会破
    `MAX_D` 则不延续（防粘连制造超长拍）。
  - 硬约束组允许超过 `MAX_D`，但有绝对上限 `HARD_CEIL = MAX_D × 1.75`（14s）；
    超长相邻组说明源字幕本身是一个长事件，交给 07 的节奏预算填补而非强切。
- **BEAT-03 [经验]** 时长窗：单拍目标 2.5s–8.0s（`MIN_D`/`MAX_D`）。
  短于下限并入下一拍；达到上限立即闭拍（硬约束组除外，见 BEAT-02b）。
- **BEAT-04 [经验]** 尾拍过短时并入上一拍，而不是制造一个 1 秒的孤儿拍。
- **BEAT-05 [强制]** 每拍标注语义角色（semantic_role）：
  `hook`（开场/提问）· `explanation`（解释）· `turning_point`（转折，
  标志词：但是/然而/其实）· `conclusion`（结论，标志词：所以/关键/总之）·
  `comparison`（对照）· `emphasis`（强调）。
- **BEAT-06 [经验]** 每拍标注 motion_policy：
  `required`（默认，必须有状态变化）· `optional` · `hold`（仅片尾结论拍，
  有意识的收束静止，必须在 pacing 里写明 hold_reason）。

`beat-plan.json` 契约（schema 见 `schemas/beat-plan.schema.json`）：

```json
{
  "beat_id": "beat_03",
  "cue_range": [3, 3],
  "start_sec": 8.0, "end_sec": 13.0, "duration_sec": 5.0,
  "narration": "（SRT 原文拼接，禁止改写）",
  "semantic_role": "turning_point",
  "narrative_shape": {"type": "reverse", "before_state": "", "change": "",
                      "after_state": "", "handoff": ""},
  "motion_policy": "required"
}
```

## 3. 常见错误

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 按字数重排时间 | 音画错位且无法校验 | 只用 SRT 时间码（SRT-01） |
| 把「20%」拆成两拍 | 数字与单位分离，信息编码层无法对应原文 | BEAT-02 |
| 机切结果直接当真 | 语义断裂的拍进入下游 | 机切=基线，导演层可复核策略与标题（不改原文） |
| 为凑时长把静音间隙算进拍 | 出现无意义尾段 | 间隙信息交给 `07-choreography.md` 的节奏预算处理 |
