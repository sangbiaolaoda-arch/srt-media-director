# 11 · Visual Grammar（视觉语法体系）

> v7.0 新增。回应「固定视觉规则 → 自适应视觉导演」。
> 关联规则：`CORE-02`（先命题后素材）、`05-global-grammar`、`04-visual-storytelling`。
> 机器实现：`runtime/visual_grammar.py`（门禁 G13）。

## 一句话

**固定视觉语法体系，不固定表达。**

一拍画面「要做什么」由**抽象语法操作**描述——因果、对比、递进、层级、强调、
并置、转场、建立、抽象；「长什么样」由导演从多种表层实现里自由挑选。
语法是稳定的，表达是自由的。

## 为什么需要它

旧架构有一个隐蔽的固定性：语义关系被硬绑到具体素材名——
`answer_to → cause_effect 模板`、`concession → comparison 模板`。
这等于说「问答戏必须长成某个样子」。素材名一旦被当成语法，导演就没有了表达自由，
画面开始千篇一律。

本模块把这条链路拆成两层：

```
语义关系   →  抽象语法操作   →  表层实现（一对多）
relations  →  grammar_ops   →  surfaces
```

## 语法操作表（固定）

| op | 含义 | 可用表层实现（示例，非穷举） |
|---|---|---|
| `establish` | 建立语境/主体 | compass / map_pin / flag / clock / hourglass |
| `causality` | 因果、结论、问答 | gears / conn_nodes / arrow_chain / bulb / puzzle |
| `contrast` | 对比、让步转折 | balance / chip_row / bar_mini |
| `progression` | 递进、序列 | arrow_chain / milestone / chart_line / tick_line |
| `hierarchy` | 层级、从属 | ring_pair / brackets / orbit / ruler |
| `emphasis` | 强调 | target / progress_ring / halftone |
| `juxtapose` | 并置 | bar_mini / chip_row / scatter |
| `transition` | 转场 | wave / spiral |
| `abstract` | 抽象氛围 | dot_grid / scatter / plus_field / cross_hatch |

关系类型到语法的映射见 `runtime/visual_grammar.py: RELATION_GRAMMAR`。

## 硬纪律（机器门禁 G13）

1. 每拍必须有一组合法语法操作（非空，且都在 `GRAMMAR_OPS` 内）。
2. **同一语法必须有多于一种表层实现**——否则语法退化成素材名，门禁失败。
3. 语法操作与素材名严格分离：`grammar_ops` 里不得出现画法名。

## 导演怎么用

- 先问「这拍在语法上做什么」（因果？对比？层级？），再问「用什么表达最好看」。
- 同样的 `contrast`，在数据片里可以是双柱对比，在叙事片里可以是天平。
- 表层实现的选择理由应能写进 `visual_claim` 的证据链，而不是「模板要求」。
