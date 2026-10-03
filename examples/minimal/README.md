# examples/minimal — 最小可运行示例

8 条字幕、38 秒，主题「睡前手机依赖」。覆盖 6 种构图策略中的 5 种：
`left_to_right_flow` / `cause_effect` / `single_focus` / `center_cluster` /
`before_after`（含数字编码：百分比环形图、前后对比柱状图）。

## 运行

```bash
# 端到端（含 L3 光栅探针帧）
python cli.py examples/minimal/attention.srt \
  --out sample --overrides examples/minimal/director_overrides.json

# 样例优先工作流（前 30 秒 + 联系表拼图）
python runtime/make_sample.py 30
```

## 文件

- `attention.srt` — 输入字幕（唯一时间真值）
- `director_overrides.json` — 导演层人工覆写示例。键 = 该拍首条字幕的 cue id；
  值可包含 `title` / `claim` / `strategy` / `keyword` / `motif` / `cause` /
  `result` / `note` 等字段。没有它流水线也能全自动运行，有它则模拟
  「导演层语义复核」（L4）的人工修订。
