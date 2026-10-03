# 05 · 全局视觉语法（Global Visual Grammar）

> 阶段产物：`visual-plan.json` 顶层的 `global_visual_grammar`
> 约束：CORE-19 / CORE-21 / CORE-22 · 与 06/07 模块的模板、门禁互为表里

## 1. 统一的是语法，不是位置

全片统一的是**表达规则**：字体层级、颜色语义、关系语汇、镜头语言、
强调语言。**不统一**的是构图模板——每拍根据命题选不同模板
（CORE-19）。「每拍都是大标题 + 居中图」是 PPT，不是统一语法。

## 2. 字体层级（Typography Language）

- **GRAM-01 [强制]** 全片使用同一套字号层级，层级差即视觉权重差：

  ```text
  eyebrow(20) < note(22) < label(26) < display_small(40) < keyword(44)
      < word(56) < number(96)
  ```

- **GRAM-02 [强制]** 层级与角色绑定：support 文本 ≤ label；
  secondary 可用 keyword；primary 文本用 word/number 级。
  任何元素不得临时发明层级之外的字号（构图门禁 `GATE-A19` 会校验
  主次尺度关系）。

## 3. 颜色角色（Color Roles）

见 `03-emphasis-and-encoding.md` §4。全局补充：

- **GRAM-03 [强制]** 颜色角色全片稳定：negative/positive/info/neutral/ink
  五角色之外不新增语义色；同角色同语义（ENC-04）。
- **GRAM-04 [经验]** 背景/面板/线条为中性纸色系（paper `#F7F4EE` /
  panel `#FFFFFF` / line `#C9C2B4`），让语义色在画面中是稀缺资源——
  稀缺才有强调力。

## 4. 关系语汇（Relation Language）

- **GRAM-05 [强制]** 关系类型与图形语汇一一对应，全片一致：

  | 关系 | 语汇 |
  |---|---|
  | 因果（causes） | 箭头 connector |
  | 流向（flow_to） | 箭头 connector（左→右） |
  | 对照（contrast） | 双面板 dual_panel（负向柔色 / 正向柔色） |
  | 归属（bound_to） | 宿主包含（元素 host 于图形/图表内） |

  新增关系类型 = 新增一条全局语法，必须在 `global_visual_grammar` 里登记。

## 5. 镜头语言（Camera Language）

- **GRAM-06 [强制]** 默认 static；`push_in` 仅用于数字强调拍且必须写
  reason（CAM-01）。全片镜头运动种类 ≤ 2 种。

## 6. 强调语言（Emphasis Language）

- **GRAM-07 [强制]** 每拍一个主注意力目标（EMP-04 / GATE-R1）。
  强调手段优先级：语义色 > 字号层级 > 位置居中 > 动效（pulse/洗色）。
  动效是最后一层，不是第一层（CORE-10）。
- **GRAM-08 [经验]** 同一拍内强调手段不超过两种叠加（语义色 + 字号
  通常已足够）。

## 7. 模板多样性

- **GRAM-09 [强制]** 邻拍不得使用相同构图模板（`GATE-R8`）。显式导演
  覆写可豁免，但需在 visual-plan 中留痕（谁覆写、为什么）。
- **GRAM-10 [经验]** 全片 8 拍应至少出现 4 种不同模板；低于此数，
  L4 审查按「疑似 PPT 化」打回（见 `10-anti-ppt.md`）。

## 8. 产出契约

```json
"global_visual_grammar": {
  "style": "paper-flat",
  "typography_language": "eyebrow < note < label < keyword < display",
  "color_roles": {"negative": "#D64541", "positive": "#2E9E63",
                  "info": "#3E7CB1", "neutral": "#8F887C", "ink": "#211D17"},
  "relation_language": {"cause": "arrow", "contrast": "dual_panel"},
  "camera_language": "static by default; push_in only for numeric emphasis",
  "emphasis_language": "one primary attention target per beat"
}
```
