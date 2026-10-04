# 贡献指南

感谢你愿意改进 SRT Media Director。本仓库同时是**方法论**与**参考实现**，
两类贡献的门槛不同，请对号入座。

## 0. 铁律

> **新增 `[强制]` 级规则必须附带机器检查。**

没有机器检查的规则在 Agent 执行时等于不存在。提交新的强制规则时，
必须同时在 `runtime/self_test.py`（12 道门禁之一或新增一门）或
`runtime/validator.py`（L1/L3）中给出可执行的校验。CI 会拦。

## 1. 改方法论（skills/）

- 一个模块只回答一类问题；新主题先考虑能否并入现有模块。
- 规则编号全仓库唯一且**只增不改**：`CORE-nn`、`GATE-Rn`、`GATE-Gn` 等。
  废弃一条规则时标记 `[已废弃，由 X 替代]`，不要回收编号——修复日志与
  历史报告按编号引用。
- 规则分三级：`[强制]`（进 CI）/ `[经验]`（默认遵守，偏离要写理由）/
  `[建议]`（参考）。升级一条规则到 [强制] 时，同步补机器检查。
- 修改模块后检查 `skills/coordinator.md` 的阶段调用表是否仍成立。

## 2. 改参考实现（runtime/）

```bash
python runtime/self_test.py    # 必须 VERIFIED，改任何一行都要重跑
```

- 新增视觉能力（motif / 图表 / 事件动作 / 镜头）：
  1. 在 `raster_renderer.py`（PIL 探针）与 `html_adapter.py`（播放器）
     **双侧实现**——只实现一侧会导致 L3 探针与播放画面不一致；
  2. 在对应技能文档登记（词汇表 / 全局语法）；
  3. 在 self_test 增加覆盖。
- 构图模板（Blueprint）新增：定义 slot 区域 + 更新 `06-composition.md`
  模板表 + 确认 R/A 门禁在新模板下的语义。
- 遵守 CORE-06 的反向约束：构图/渲染层**不替导演层做叙事决策**；
  发现内容问题时抛错回上游（如 `LayoutIntentIncomplete`），不要静默修复。

## 3. 改 Schema（schemas/）

- Schema 是层间契约：字段只增不删；破坏性变更需要 major 版本号升级
  （见 `CHANGELOG.md` 的版本约定）。
- 改了 Schema 就必须同步改对应的产出方 Runtime 模块与 validator。

## 4. 提交样例（examples/）

欢迎新示例（quantitative / comparison / transformation 等类型）。
一个合法示例 = `*.srt` + `director_overrides.json` + `README.md`
（说明覆盖了哪些策略/编码），且 `python cli.py <srt>` 全绿。

## 5. 流程

1. Fork & branch：`feat/<主题>` 或 `fix/<规则编号>-<简述>`。
2. Commit message 引用规则编号（如 `fix(GATE-R5): eyebrow 区域挪入安全区`）。
3. PR 描述包含：动机 / 触动的规则编号 / self_test 结果截图或日志。
4. 不要提交 `sample/`、`out/` 等产物目录（见 `.gitignore`）。

## 6. 行为准则

对事不对人。讨论规则时用证据（渲染帧、校验报告、失败用例），
不用「我觉得更好看」。
