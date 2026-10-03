---
name: srt-media-director
version: 4.4.0
status: public-learning-and-execution
language: zh-CN
agent_created: false
license: MIT
description: >-
  面向 AI Agent 的开源信息图动画导演 Skill：SRT → 语义分析 → Beat → 叙事形状 →
  Visual Claim → 强调与信息编码 → 视觉叙事 → 全局语法 → 构图 → 时序编排 →
  Visual DSL → 布局/编译 Runtime → 适配器 → 分层验证 → 局部修复。
  v4.0 将 v3.0 单文档重组为「11 个模块技能 + 主协调器 + 可运行参考 Runtime」，
  全部硬规则保留并配上机器门禁（runtime/self_test.py 8 道门禁已验证）。
---

# SRT Media Director（v4.0 开源版入口）

> 本文件是仓库级入口。执行任务的 Agent 请直接跳转：
> **统筹技能包 → [`skills/coordinator.md`](skills/coordinator.md)**
> 模块导航 → [`skills/README.md`](skills/README.md)

## 这是什么

把一段带时间轴的字幕（SRT）变成**有视觉层级、空间关系、信息编码、
时间节奏与可验证性**的动画信息场景——而不是把字幕排成 PPT。

v4.0 相对 v3.0 的变更：方法论不变，载体重组。

| v3.0 | v4.0 |
|---|---|
| 单文档 ~6900 行 | 11 个模块技能 + 主协调器（`skills/`） |
| 编号重叠（§10.16 出现两次）、版本残留 | 全仓库唯一规则编号（`CORE-nn` 等），编号不随文档重组变化 |
| 规则靠自觉 | 规则分 [强制]/[经验]/[建议] 三级；[强制] 级全部有机器门禁 |
| Runtime 是「应有」 | Runtime 是「已有」：`runtime/` 参考实现 + `self_test.py` 8 道门禁 CI 可跑 |

## 30 秒上手

```bash
pip install pillow jsonschema

# 1. 先验证 Runtime（Bootstrap Gate，VAL-03）
python runtime/self_test.py          # 8 道门禁 → SELF-TEST VERIFIED ✔

# 2. 跑最小示例（8 条字幕 / 38 秒 / 5 种构图模板）
python cli.py examples/minimal/attention.srt \
  --out sample --overrides examples/minimal/director_overrides.json

# 3. 样例优先工作流（CORE-13）：前 30 秒 + 联系表拼图
python runtime/make_sample.py 30
```

产物：`sample/work/*.json`（全部中间层）· `sample/preview/<beat>/*.png`
（L3 真实探针帧）· `sample/sheet.jpg`（联系表）· `sample/film/index.html`
（自包含播放器，浏览器打开即播）。

## 仓库地图

```text
srt-media-director/
├─ SKILL.md                  # 本文件：入口
├─ skills/                   # 方法论（为什么 / 做什么）
│  ├─ coordinator.md         #   ★ 主协调器：阶段调用表 / 决策点 / 终止条件
│  ├─ 00-core-contract.md    #   核心契约（24 条，最高优先级）
│  ├─ 01-srt-and-beats.md    #   SRT 时间真值 + Beat 切分
│  ├─ 02-narrative-shape.md  #   叙事功能与认知变化
│  ├─ 03-emphasis-and-encoding.md  # 强调计划 + 数字信息编码
│  ├─ 04-visual-storytelling.md    # Visual Claim + 证据纪律
│  ├─ 05-global-grammar.md   #   全局视觉语法
│  ├─ 06-composition.md      #   构图系统（Thesis/Blueprint/门禁 R1-R8）
│  ├─ 07-choreography.md     #   时序编排（lifecycle/cue/交接 G1-G5）
│  ├─ 08-dsl.md              #   Visual DSL 规范（禁像素）
│  ├─ 09-validation-repair.md      # 四层验证 + 修复路由
│  └─ 10-anti-ppt.md         #   防退化质量底线
├─ runtime/                  # 参考实现（怎么算 / 机器事实）
│  ├─ srt_parser.py  beat_planner.py  visual_director.py
│  ├─ composition_planner.py  entrance_planner.py
│  ├─ raster_renderer.py  html_adapter.py  validator.py
│  ├─ pipeline.py  make_sample.py  self_test.py  common.py
├─ schemas/                  # 6 个中间产物的 JSON Schema
├─ examples/minimal/         # 8-cue 最小示例 + 导演覆写示例
├─ cli.py                    # 命令行入口
└─ .github/workflows/        # CI：每次 push 跑 self_test
```

## 核心契约（摘要，全文见 `skills/00-core-contract.md`）

1. SRT 是唯一时间来源；旁白原文不得被导演改写。
2. 视觉不是字幕的复制品；先命题后素材。
3. 导演层不猜像素；`film/index.html` 是编译产物，禁止手改。
4. 动画必须有目的；Fade In 不算动画设计。
5. 技术验证（L1-L3，机器）与审美验证（L4，人/Agent）必须分开。
6. 修复必须回到正确上游层；样例优先，禁止直接渲全片。
7. 能力不存在时：等价实现 → 简化 → 阻断报告。禁止编造。

## License

MIT（见 `LICENSE`）。欢迎按 `CONTRIBUTING.md` 提交模块级改进——
新增 [强制] 规则必须附带机器检查，否则没有牙齿。
