---
name: srt-media-director
description: >-
  面向 AI Agent 的开源信息图动画导演 Skill：把一段带时间轴的字幕（SRT）编译成
  有视觉层级、空间关系、信息编码与时间节奏的动画信息场景，而不是把字幕排成 PPT。
  流水线为 SRT → 语义分析 → Beat → 叙事形状 → Visual Claim → 强调与信息编码 →
  视觉叙事 → 全局语法 → 构图 → 时序编排 → Visual DSL → 布局/编译 Runtime →
  适配器 → 分层验证 → 局部修复；规则分 [强制]/[经验]/[建议] 三级，[强制] 级全部
  配有机器门禁（runtime/self_test.py）。当用户需要从 .srt/字幕生成信息图动画、
  需要「固定审美原则 + 自适应视觉风格」的可验证视觉导演，或需要一套带机器门禁的
  开源参考实现时使用。
license: MIT
metadata:
  version: "7.6.0"
  status: public-learning-and-execution
  language: zh-CN
  agent-created: false
---

# SRT Media Director

> 本文件是仓库级入口。执行任务的 Agent 请直接跳转：
> **统筹技能包 → [`skills/coordinator.md`](skills/coordinator.md)**
> 模块导航 → [`skills/README.md`](skills/README.md)

## 这是什么

把一段带时间轴的字幕（SRT）变成**有视觉层级、空间关系、信息编码、
时间节奏与可验证性**的动画信息场景——而不是把字幕排成 PPT。

v4.0 相对 v3.0 的变更：方法论不变，载体重组。

| v3.0 | v4.0 |
|---|---|
| 单文档 ~6900 行 | 18 个模块技能 + 主协调器（`skills/`） |
| 编号重叠（§10.16 出现两次）、版本残留 | 全仓库唯一规则编号（`CORE-nn` 等），编号不随文档重组变化 |
| 规则靠自觉 | 规则分 [强制]/[经验]/[建议] 三级；[强制] 级全部有机器门禁 |
| Runtime 是「应有」 | Runtime 是「已有」：`runtime/` 参考实现 + `self_test.py` 20 道门禁 CI 可跑 |

### v7.1：参考帧构图语法

| 学的是（构图代码） | 不是只学（表面） |
|---|---|
| 版心网格 / 圆角卡片 / 描边阶梯 | 单一配色 |
| 线稿图标 / 连接箭头 / 强调纪律 | 单个素材 |
| 逐元素入场编排（rise/fade/pop/draw/grow） | 整拍淡入 |

### v7.2：从「抄三张图」到「生成引擎」

判据只有一条：**一条规则若只能还原它被抽出的那张图，就是「抄」；若还能外推出源图没有的解，才是「学」。**

| 维度 | 照抄（模板动物园） | 学会（规则引擎） |
|---|---|---|
| 坐标 | 写死 `x=[48,265,482]` | `cols(3)` 公式的解 = 那个坐标 |
| 列数 | 只能 3 列 | `cols(n)` 任意 n，仍贴版心不重叠 |
| 强调 | 颜色计数 | 预算：含强调色的**元素个数** ≤ 1 |
| 新构型 | 做不出 | 四象限 / 时间轴 / 纵向清单 |
| 门禁 | 无 | G16：复现 + 泛化双断言 |

### v7.0：自适应视觉导演

| 固定（不变） | 不固定（随内容自适应） |
|---|---|
| 审美原则（层级/对比/静默/必要性） | 视觉风格（家族/情绪/密度） |
| 视觉语法体系（causality/contrast/progression…） | 表层表达（用哪种画法实现该语法） |
| 编译与验证规则（门禁/契约/风格锁） | 画面长相（构图模板降为建议锚点） |

## 30 秒上手

```bash
pip install pillow jsonschema

# 1. 先验证 Runtime（Bootstrap Gate，VAL-03）
python runtime/self_test.py          # 20 道门禁 → SELF-TEST VERIFIED ✔

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
│  ├─ 10-anti-ppt.md         #   防退化质量底线
│  ├─ 11-visual-grammar.md   #   视觉语法体系（抽象语法替代素材名）
│  ├─ 12-style-bible.md      #   视频级视觉人格（风格随内容自适应）
│  ├─ 13-reference-frames.md #   参考帧构图语法（学构图代码，非抄配色）
│  ├─ 14-intent-layer.md     #   语义视觉意图层（Agent 不再「画画」）
│  ├─ 15-runtime-architecture.md   # Runtime 六包架构 + 生成-截图-评审-修复闭环
│  ├─ 16-behavior-spec.md    #   行为规范 42 条（视觉导演 + 编译器）
│  └─ 17-scene-compiler.md   #   场景编译层（Scene Compiler）
├─ runtime/                  # 参考实现（怎么算 / 机器事实）
│  ├─ srt_parser.py  beat_planner.py  visual_director.py
│  ├─ composition_planner.py  entrance_planner.py
│  ├─ raster_renderer.py  html_adapter.py  validator.py
│  ├─ visual_grammar.py  style_bible.py  visual_necessity.py
│  ├─ ref_frame.py           #   参考帧构图语法 + 逐元素入场图层规范
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
