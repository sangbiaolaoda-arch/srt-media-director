# 12 · Style Bible（视频级视觉人格）

> v7.0 新增。回应「固定视觉规则 → 自适应视觉导演」。
> 关联规则：`CORE-07`（能力边界）、`05-global-grammar`、`10-anti-ppt`。
> 机器实现：`runtime/style_bible.py`（门禁 G14）。

## 一句话

**固定审美原则，不固定视觉风格。**

`style_tokens.json` 锁的是**项目级物料**（调色板 / 字体 / 线宽）——保证不漂移。
Style Bible 描述的是**视频级人格**——由这一条片子的内容推导出来，保证气质随内容自适应。

两者互补：tokens 让画面「不跑色」，bible 让画面「合气质」。

## 人格字段（固定字段，不固定取值）

| 字段 | 取值域 | 由什么推导 |
|---|---|---|
| `family` | editorial_flat / editorial_textured / technical_diagram / cinematic_muted | 内容类型（当前默认 editorial_flat） |
| `mood` | neutral / tense / warm / cold / calm | 全片句子情绪分布的主导 mood |
| `density` | sparse / balanced / dense | 全片平均句长（<12 / 12–24 / >24） |
| `typography` | scale / face / contrast | 固定字阶语言 |
| `motion_temperament` | restrained / measured / expressive | 动势基调 |
| `contrast_policy` | wcag_aa / wcag_aaa / high | 可读性政策（默认 wcag_aa） |
| `silence_policy` | 文本条件式 | 停留下限（与契约层一致） |

## 硬纪律（机器门禁 G14）

1. 七个必填字段齐全。
2. 每个字段取值必须落在合法取值域内。
3. bible 必须是「推导结果」：换一段内容，`mood` / `density` / `narrative_roles` 应随之变化。

## 导演怎么用

- 开拍前先读 bible：这条片子整体什么气质、多密、什么对比政策。
- 逐拍的局部决策（策略/密度/强调）必须与 bible 一致——偏离要写明理由，
  否则就是风格漂移（`style_guard` 会拦）。
- bible 不进渲染器，它是**导演自检的执照**：回答「我这一拍的选择，配得上这条片子的气质吗」。

## 与 tokens 的分工

```
style_tokens.json   项目级  颜色/字体/线宽的封闭集合   → 不许出新颜色（物理锁）
style_bible        视频级  气质/密度/倾向的开放描述   → 允许表达自由（语义锁）
```
