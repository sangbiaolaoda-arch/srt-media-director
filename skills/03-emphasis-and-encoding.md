# 03 · 强调与信息编码（Emphasis & Information Encoding）

> 阶段产物：`visual-plan.json` 内的 `emphasis_plan` 与 `information_encoding`
> 上游：02-narrative-shape · 下游：04-visual-storytelling、06-composition
> 参考实现：`runtime/visual_director.py`

## 1. 强调候选：从原文出发，不凭空发明

- **EMP-01 [强制]** 强调候选必须带 `source_span`（原文片段）。候选类型：
  `keyword`（风险词/安全词等语义负载词）· `percentage`（百分比）·
  `number`（数量级）· `phrase`（关键短语）。
- **EMP-02 [强制]** 候选要标注语义角色：`risk` / `safety` / `part_to_whole`
  / `magnitude` 等。语义角色决定颜色（CORE-22），不是装饰。
- **EMP-03 [经验]** 排序依据：叙事功能优先（结论拍的关键词 > 解释拍的
  普通名词）→ 信息密度（含数字者优先）→ 新鲜度（前文未出现者优先）。

## 2. 每拍一个注意力终点

- **EMP-04 [强制]** 每拍恰好一个 `primary_emphasis`（与构图门禁
  `GATE-R1` 互为表里）。次强调（secondary_emphasis）最多 2 个，
  且必须服务于主要强调。
- **EMP-05 [强制]** 强调必须有宿主：被强调元素要么自身是图形主体，
  要么通过 `host` 字段绑定到一个图形/图表元素（例如大号数字 hosted
  在环形图上）。没有宿主的强调是漂浮的字幕，违反 CORE-03。
- **EMP-06 [经验]** 幽灵大字：关键词/数字可再以特大字号、低透明度
  （≈14%）垫在主体之下的 decor 层重复一次——它是强调的「环境回声」，
  不抢注意力，只强化记忆点。每拍至多一个，且文本必须与 primary 强调一致
  （不得引入新信息）。

## 3. 信息编码决策树

数字不是文字，是**数据**。遇到数字先做编码决策，再决定画法：

| 原文形态 | 编码类型 | 视觉表达 | 主次安排 |
|---|---|---|---|
| `X%`（部分/整体） | `part_to_whole` | 环形图（donut）+ 居中关键数字 | 数字为 Primary，图表为宿主 |
| `A → B`（随时间变化） | `change_over_time` | 前后双柱（bars）+ delta 徽标 | 图表为 Primary，delta 为 Secondary |
| 两个对立概念同拍出现 | `semantic_color_pair` | 双面板对照（红/绿语义色） | 负向词 Primary，正向词 Secondary |
| 只有关键词，无数字 | `typography` | 字重/字号层级 + 语义色 | 关键词 Primary，motif 为宿主 |

- **ENC-01 [强制]** 编码决策必须记录 `data_span`（对应原文的数字片段），
  L4 审查据此核对图表数值与原文一致（防编造，CORE-14）。
- **ENC-02 [强制]** 同一拍内不混用两种数字编码（环形图 + 柱状图同拍 =
  两个注意力终点，违反 EMP-04）。
- **ENC-03 [经验]** 图表只做「让观众更快理解数字关系」这一件事；
  不要为了显得专业而给不需要图表的拍加图表。

## 4. 颜色即编码

语义色是第二编码通道，不是配色风格：

```text
negative  #D64541  危险 / 风险 / 失败 / 负向路径
positive  #2E9E63  安全 / 保护 / 通过 / 正向路径
info      #3E7CB1  关键数字 / 中性信息
neutral   #8F887C  辅助说明
ink       #211D17  正文 / 结论
```

- **ENC-04 [强制]** 同一语义在全片使用同一颜色角色（全局语法的一部分，
  见 `05-global-grammar.md`）。红色不能这一拍表危险、下一拍表强调。

## 5. 反模式

- 把整句旁白标成「强调」——等于没有强调；
- 数字进了图表但画面里找不到原值——L3/L4 无法核对，打回；
- primary_emphasis 选了装饰性词（「的」「了」所在的片段）——
  说明候选提取没有按语义角色过滤。
