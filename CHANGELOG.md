# Changelog

## [7.4.0] — 2026-10-05

**Runtime 六包架构 + 生成→截图→Critic→修复闭环。** 把 runtime 从「一堆平铺模块」
重构为职责清晰的六包，并落地用户要的闭环：

```
Agent → VisualIntent → Compiler → RenderPlan → HTML/SVG → 截图 → 检查 → 修复
```

### Added

- **`runtime/director/`**（Agent 视觉决策层）：`visual_intent.py`（意图契约，零坐标）、
  `grammar.py`（语法词表 + 可读描述）、`relationship.py`（关系图：sinks/dot 导出）、
  `critic.py`（机器 Critic：截图+规范→判决+修复路由）。
- **`runtime/compiler/`**（几何层）：`composition.py`（语法 1:N 实现 + coverage）、
  `constraints.py`（编译期约束门禁）、`layout.py`（槽位求解）、`svg_compiler.py`（DSL→SVG/HTML）。
- **`runtime/render/`**（渲染层，多后端可降级）：`html_renderer.py`、
  `playwright_renderer.py`（有则用）、`screenshot.py`（playwright > chromium CLI > cairosvg）。
- **`runtime/validation/`**（渲染后校验）：`geometry.py` / `typography.py` /
  `safe_area.py` / `visual_regression.py`。
- **`runtime/primitives/`**（图元工厂，函数化可复用）：`text/shape/path/chart/connector/motif.py`。
- **`runtime/schemas/`**（中间语言 JSON Schema）：`visual_intent.json` / `visual_plan.json` / `render_plan.json`。
- **`runtime/director_loop.py`**：把六包串成闭环；FAIL 时 `route()` 找上游层并确定性修复后重编重截。
- **门禁 G19**（架构）：断言六包与目标文件布局存在、跨包接线可用、后端如实探测。
- **门禁 G20**（闭环）：断言闭环**真的渲染出 PNG 并 PASS**，且问题码路由回正确上游层。
- 技能文档 `skills/15-runtime-architecture.md`。

### Changed

- `self_test.py` 门禁 18 → **20**；版本 `7.3.0` → `7.4.0`。
- 顶层模块（`intent_layer` / `composition_compiler` / `visual_grammar` / `ref_frame` /
  `composition_planner`）保留为**单一逻辑源**，新包作为规范 facade，不重复实现逻辑。

### Notes

- 渲染后端优先级 playwright > chromium(CLI) > cairosvg；纯 Python 环境也能跑，CI 不依赖浏览器。
- 三设计红线：Agent 不画画（零坐标）/ 语法≠模板（1:N）/ 能力如实报告（不假装有 Playwright）。

## [7.3.0] — 2026-10-05

**从「模板选择器」升级为「语义视觉意图层」。** Agent 不再负责「画画」，只负责
「这句话应该被怎样视觉化」；几何由 Runtime 决定。

分界线（对照参考 Runtime 的两个例子）：

```jsonc
// 错误：模板选择器（Agent 被训练成选模板）——被门禁 G17 拒斥
{"strategy": "cause_effect", "template": "left_to_right_flow",
 "hero_x": 300, "hero_y": 400}

// 正确：视觉意图（Agent 表达语义，Runtime 决定几何）
{"visual_claim": "small_repeated_actions_accumulate_into_large_change",
 "grammar": ["accumulation", "trajectory", "threshold"],
 "focal_point": "trajectory",
 "relationship": [{"from": "small_actions", "relation": "accumulate_into", "to": "trajectory"},
                  {"from": "trajectory", "relation": "crosses", "to": "threshold"}],
 "density": 0.62, "silence": false, "motion_intent": "accumulate_then_reveal"}
```

### Added

- **`runtime/intent_layer.py`**（Agent 语义层）：定义视觉意图契约 + 校验 +
  `template_leak_keys()` / `is_template_selector()`（拒斥 strategy/template/像素键）。
  `derive_intent(beat)` 从一拍推导意图，输出**零坐标**。
- **`runtime/composition_compiler.py`**（Runtime 几何层）：`compile_intent(intent)`
  把意图编译为视觉 DSL。**语法 → 实现是 1:N 映射**（不是「语法==模板」），
  坐标全部来自 `ref_frame` 的规则（`cols/rows/stroke`），density/silence 决定槽数。
  新增复合实现 accumulation+trajectory+threshold。
- **`schemas/visual-intent.schema.json`**：视觉意图 JSON Schema；`additionalProperties: false`
  从 schema 层就堵死像素/模板键。
- **门禁 G17**（意图层）：断言「模板选择器被拒斥 + 视觉意图通过 + 推导意图无泄漏」。
- **门禁 G18**（编译器）：断言「意图→合法 DSL、强调≤1、语法 1:N、每个语法都有实现」。
- 技能文档 `skills/14-intent-layer.md`。

### Changed

- `visual_grammar.GRAMMAR_OPS` 新增 `accumulation` / `trajectory` / `threshold`。
- 构图从「Agent 选 `strategy`」改为「Agent 给 `grammar` → 编译器选实现」。
  旧 `strategy` 路径保留（向后兼容），但不再是推荐入口。
- `self_test.py` 门禁 16 → **18**；版本 `7.2.0` → `7.3.0`；黄金基准因语法表扩展而重生成。

### Notes

- 视觉证据：`runtime/_build_intent_demo.py` 渲染「意图→构图」两帧
  （`intent-to-composition.png`）：同一个编译器把 accumulation 组合编译成
  「累积短柱 → 上升轨迹（焦点，唯一强调）→ 阈值虚线」，把 contrast 编译成双槽对比。

## [7.2.0] — 2026-10-05

**从「抄三张参考帧」升级为「生成引擎」。** 判据：一条规则若只能还原它被抽出的
那张图就是「抄」，若还能外推出源图没有的解才是「学」。

### Added

- **`runtime/ref_frame.py` 规则引擎化**：把参考帧的写死坐标/写死列数改为**规则**——
  - `cols(n)` / `rows(n)`：分槽规则。`cols(3)` 精确复现参考帧 `x=[48,265,482]`（列宽 150），
    `cols(2,gap=32)` 复现 `x=[48,356]`（面板宽 276）；同时可外推到 n=4/5。
  - `stroke(role)`：描边角色规则（强调=加粗+加深，次级统一同一灰）。
  - `type_scale(name)`：字阶规则。
  - `count_accent(spec)`：强调**预算**（含强调色的元素个数 ≤ 1，非颜色串次数）。
  - `audit_spec(spec)`：图层规范机器门禁（可独立渲染/框在画布内/motion 合法/强调≤1）。
- **三个参考帧没有的新构型**（同规则外推）：`frame_quadrants`（2×2）、
  `frame_timeline`（等距时间轴）、`frame_stack`（纵向清单）。
- **门禁 G16**（`runtime/self_test.py`）：断言「复现参考帧**且**泛化到新构图」，非照抄。
- 技能文档 `skills/13-reference-frames.md` 新增「代码经验总结」附录（七条可迁移经验）。

### Changed

- 旧版式 `frame_hero/statement/chain/bar_detail/compare` 全部改为**规则调用示例**，
  不再含写死版式坐标；签名向后兼容（旧脚本仍可跑，见 self_test G16 smoke）。
- `self_test.py` 门禁 15 → **16**；版本 `7.0.0` → `7.2.0`。

### Notes

- 泛化视觉证据：`runtime/_build_generalize.py` 渲染「上排复现 / 下排外推」并排图
  （`ref-rule-generalize.png`），6 帧墨量各异、外推帧与复现帧结构差异显著。

## [7.1.0] — 2026-10-04

参考帧构图语法：把参考帧的手写 SVG 构图学成可复用模块（版心网格 / 圆角卡片 /
线稿图标 / 连接箭头 / 强调纪律 / 逐元素入场编排），而非只抄配色。新增技能文档
`skills/13-reference-frames.md`；`runtime/ref_frame.py`（逐元素图层规范）；
逐元素入场渲染 `_build_refanim.py`。

## [7.0.0] — 2026-10-04

「固定视觉规则 → 自适应视觉导演」架构级升级。原则：

> **固定审美原则，不固定视觉风格；固定视觉语法体系，不固定表达；
> 固定编译/验证规则，不固定长相。**

不推翻 v6.x，在其之上做加法：把「写死的模板与数量」换成「可自适应的语法与必要性」。

### Added

- **Visual Grammar**（`runtime/visual_grammar.py`，门禁 G13）：把语义关系编译为
  **抽象语法操作**（establish / causality / contrast / progression / hierarchy /
  emphasis / juxtapose / transition / abstract），每个语法操作对应**多种**表层实现
  （画法名）。语法到表达是一对多，导演可自由挑选；`answer_to→causality`、
  `concession→contrast` 等映射集中在此。断开了旧架构「语义关系 → 固定模板/素材名」的硬绑。
- **Style Bible**（`runtime/style_bible.py`，门禁 G14）：**视频级视觉人格**，由本条
  内容推导——`family / mood / density / typography / motion_temperament /
  contrast_policy / silence_policy`。与项目级 `style_tokens.json`（物理锁：颜色/字体/
  线宽）互补，bible 是「气质锁」：换一段内容，人格随内容变化。
- **Visual Necessity**（`runtime/visual_necessity.py`，门禁 G15）：每个元素必须能被
  「**删除它，这一拍的 Visual Claim 会变弱吗**」论证。分 `required / supporting /
  optional`；只有「既非氛围、又不承载信息、删掉无损」的元素才判 UNJUSTIFIED。
- 技能文档 `skills/11-visual-grammar.md`、`skills/12-style-bible.md`。

### Changed

- **P0① 构图模板降为建议锚点**（`runtime/composition_planner.py`）：新增
  `COMPOSITION_POLICY`（`templates_are: advisory`、`free_placement: True`）；
  元素可自带归一化 `rect` 自由落位绕开模板，未知 slot 无区域时仍拒绝猜坐标
  （`LAYOUT_INTENT_INCOMPLETE`）。固定审美原则，不固定长相。
- **P0② 数量门禁改软**（`runtime/self_test.py`）：「每拍 ≥3 图形要素」硬门禁删除，
  改由必要性审计（G15）承担——数量成为结果，而非约束。
- 导演层接入：`visual-plan.global_visual_grammar` 增加 `style_bible` 与
  `grammar_language`；每个 beat 的 DSL 增加 `grammar_ops`。
- `self_test.py` 门禁 12 → 15；黄金基准重生成（产物新增字段）。

### Notes

- 全链路实测：`self_test` 15/15、`pytest` 全绿、60s 样片 `pipeline` PASS、
  grammar / necessity 审计 PASS。本次不新增素材/特效（按优先级，素材放最后）。

## [6.1.0] — 2026-10-04

回应「作为主体的文字太淡、像背景」的可读性反馈。

### Fixed

- **主体文字对比度过低**（`runtime/common.py` · `runtime/raster_renderer.py` ·
  `runtime/html_adapter.py` · `runtime/style_tokens.json`）：
  - 旧主题主墨色 `#494343` 在暖米底 `#E9E4DE` 上只有 ≈3:1；语义色
    （红 `#E14D49` / 图示蓝灰 `#787C90` / 绿 `#AFCAC1`）落在 ≈2:1，主体文字
    在浅底上「发灰、读起来像背景」。
  - 主墨色加深为暖黑 `#26221E`；新增三个**主体语义文字加深变体**
    `text_negative #A8281F` / `text_positive #2E5A4A` / `text_info #33374D`。
  - 文字层一律经 `_text_color()` / `textColor()` 取加深色，图形/装饰仍用原
    语义色，保证「文字够重、图形仍鲜活」。
  - 实测：主体文字对比度由 ≈1.9–2.9 提升到 **5.10:1**（跨过 WCAG AA 4.5:1）。
  - 风格锁定扫描（`style_guard`）token 表同步更新；黄金基准重生成。

### Notes

- 本次仅改文字取色，不改构图、时序、分拍与图形语汇；`self_test` 12/12、
  `pytest` 全绿。

## [6.0.0] — 2026-10-04

本轮把「静音信息图」的**生成 → 检查 → 定位 → 修复**闭环补成机器保证，
回应最常见的失败：画面一闪而过、转场接不上、风格漂移、构图撞车。

### Added

- **生成后契约层**（`runtime/contracts.py`，接入 `pipeline`，未过即阻断）：
  - 每拍 `end_state`（visible / positions / hold_ms）与 `transition_in`
    （carry / cut / dissolve 三选一，必须写 reason）。
  - **转场三类型机器检查**：carry 的元素必须在上一拍 end_state 且位移在容差内
    （否则要声明 transform）；cut 必须新旧构图有差异（否则「这不是转场，只是
    闪一下」）；dissolve 必须至少一个 carried（否则「空溶解」）。
  - **静音停留下限**：`hold ≥ min(阅读时间, 本拍时长) × 0.22`，低于即阻断。
  - **视线路径 attention_path**：≤4，按入场波次时间序，primary 必在且最强；
    只纳入有信息量元素（排除 decor / ambient）。
  - **ambient 持续微动**：主元素禁止 ambient；幅度上限；久静标 WARN。
  - **反空话过滤**：视觉命题/关键文本禁「高级感/科技感/震撼/有张力」等，
    要求可画描述。
- **风格锁定**（`runtime/style_tokens.json` + `runtime/style_guard.py`）：
  编译产物出现 token 外颜色 / 线宽 / 字体即 FAIL。风格一致性不靠提示词。
- **节拍表 + 末帧联系表**（`runtime/beat_sheet.py`、`runtime/lastframe.py`）：
  渲染前生成纸张评审用的节拍表 md；只渲染每拍末帧拼成 contact sheet，
  在花整片渲染成本前先看结构。
- **故障 → 修复层路由**（`runtime/repair_routing.py`、`runtime/diagnose.py`）：
  症状映射到归属层（contract / transition / token / layout / visual_claim /
  semantic）与修复动作；`RepairBudget` 每拍单变量重拍预算默认 3 次，超预算阻断，
  杜绝无限返工。

### Fixed

- **同拍断句粘连**：`beat_planner._join_texts` 旧实现用 `"".join`，导致上一句
  结尾与下一句开头粘在一起（「半点不由人」+「说这句话的人」→「半点不由人
  说这句话的人」）。改为缺标点处补逗号，断句合理。
- **短拍波次挤爆门禁**：短拍下固定归一化波次锚点会把相邻波次压到 0.25s 内，
  触发 G2 误报。`entrance_planner._respace_cues` 按最小间隔重排真实入场时刻，
  放不下时合并最近的相邻波次（= 同一时刻入场），lifecycle 同步更新。

### Changed

- `self_test.py` 门禁 8 → 12：新增生成后契约、风格锁定、语义断句、故障路由。
- 黄金基准因断句修复变更中间产物，已人工确认后重生成。

## [5.0.0] — 2026-10-04

本轮聚焦「可信度」，把主观口号落成可验证事实（P0 四项）。

### Changed

- **默认底色改为米白纸感 `#F4EFE6`**（`common.THEME`：`cinema`→`paper`）。
  浅底上连带调整：暗角 0.42→0.08、胶片颗粒 5→3、去掉黑遮幅、
  幽灵字/水印透明度上调（0.10/0.15 → 0.14/0.20）。5 套情绪调色板
  （`common.PALETTES`）全部换成米白系，强调色由金改为赭。
- **`ink_stats` 改为主题无关的高通法**：旧实现用「与单一底色固定差值」
  判定墨迹，换浅底后会把整片渐变+暗角误判成内容（实测墨迹比 0.78）。
  改为与「局部高斯模糊背景估计」比对，渐变/暗角/颗粒归为背景，
  仅真实内容计墨——阈值在深/浅底上语义一致。
- **`_draw_glow_panel` 浅底适配**：暗色主题的同心椭圆光晕在浅底上会糊，
  改为浅色圆角色块 + 同色细边。

### Added

- **真实样例库**（`examples/showcase/`）：4 类内容各一段成片 + GIF 预览——
  技术讲解（因果链/中英混排）、叙事抒情（问答/让步）、数据对比（数字/前后）、
  长片（3m41s，模板复用与调色板分布）。生成脚本 `tools/make_showcase_srt.py`。
- **已知失败案例**（`examples/known-failures/README.md`）：F01 SRT 缺空行
  导致解析退化、F02 同质内容不被误判、F03 曾存在的跨进程不可复现（已修复）、
  F04 缺 CJK 排版门禁、F05 模板覆盖缺口、F06 镜头运动仅 1 种。
- **重复感量化门禁（REP）**（`runtime/rep_metrics.py`）：模板连续拍数、
  模板分布熵、相邻拍相似度（模板/区域/调色板/装饰加权和）、调色板占比、
  装饰复现间隔；WARN/FAIL 两级，接入 `validator` L2 层。
- **黄金回归测试**（`tests/golden/` + `tests/test_golden.py`）：固定 SRT →
  五层中间产物归一化哈希比对（剔除 volatile 键 + sort_keys + 定长浮点）。
- **SVG 后端抽象**（`runtime/svg_backend.py`）：cairosvg 主 / resvg 备 /
  缺失时明确降级；`--probe` 供 CI 验证降级路径。
- **真 CI 矩阵**（`.github/workflows/ci.yml`）：Python 3.9–3.12 ×
  Linux/macOS/Windows 十二组合，显式处理三平台 cairosvg 系统依赖；
  另有 `golden`（哈希回归）与 `svg-fallback`（无系统 cairo 降级）两个 job。
- `requirements.txt` 增 `pytest`；`pyproject.toml` 增 `test` extra。

### Fixed

- **跨进程不可复现**（黄金测试上线当天抓到）：`semantic_grouper` 蝉联检测
  用 `sorted(strong, key=len)[-1]` 取锚点，长度并列时依赖集合迭代序，
  受 `PYTHONHASHSEED` 影响导致 `beat-plan.json` 跨进程哈希漂移。改为
  `sorted(strong, key=lambda g: (len(g), g))[-1]`，消除进程间差异并有回归测试。
- **WARN 误判为 FAIL**：`validator` 曾把 REP 的 WARN 级问题也计入阻断，
  与「WARN 只记录不阻断」契约冲突；状态判定改为仅非 warn 项阻塞。

## [4.4.0] — 2026-10-03

### Added

- **SVG 画法库大规模扩库**（`runtime/svg_art.py`）：主体 motif 5 → 24
  （新增图表类 `chart_bar`/`chart_line`/`progress_ring`/`cumulative`，小物件类
  `key`/`envelope`/`calendar`/`flag`/`balance`/`bulb`/`bookmark`/`lock`/
  `hourglass`/`map_pin`/`gears`/`trophy`/`compass`/`puzzle`/`target`，
  全部非拟人），装饰附体 4 → 16（新增 `wave`/`scatter`/`brackets`/`halftone`/
  `cross_hatch`/`spiral`/`bar_mini`/`ruler`/`plus_field`/`orbit`/`arrow_chain`/
  `milestone`）。合计 41 种矢量画法，`audit_svg` 越界门禁 0 违例。
- **装饰附体受控随机**（`visual_director._decor`）：种子 = `md5(beat_id +
  narration)`，装饰的**种类/落位/尺度**在规则内随拍变化；「最近 4 拍用过的
  装饰冷却」避免邻拍雷同；每拍装饰 ≥3 件（策略主题 + 随机陪衬）。
  回应「重复使用、根本没有随机感」——旧实现装饰坐标按 6 套模板写死。
- **分段情绪背景调色板**（`common.PALETTES` + `mood_palette`）：按字幕情绪选
  5 套渐变（night/warm/cold/tense/calm），PIL 渲染器按拍缓存、HTML 播放器
  按拍建渐变；全片不再是一个颜色。回应「背景颜色不好看」。
- **motif 词汇表扩充**：`_MOTIF_MAP` 由 16 词扩到 ~60 词，覆盖本片母题
  （赢→trophy / 承认→key / 结案→lock / 重来→calendar / 没说完→envelope …）。

### Changed

- `dsl.version` 4.1 → 4.4；每拍新增 `palette` 字段（情绪调色板名）。
- `self_test` 构图门禁：decor ≥2 → **≥3**（响应「每拍至少三个要素」）。
- 新增工程配套：`requirements.txt`、`pyproject.toml`、`Makefile`、
  `ARCHITECTURE.md`（架构与数据流说明），使仓库可直接 `pip install` /
  `make test`。

### Fixed

- 用户反馈「画面太素 / 只画箭头等简单图标 / 装饰重复无随机 / 背景丑」：
  v4.4 从画法库、装饰编排、背景三层同时扩量与去同质。

## [4.3.0] — 2026-10-03

### Added

- **语义检索驱动分拍**（`runtime/semantic_grouper.py`）：切拍前对 cue 序列做
  规则式中文语义检索，产出 `answer_to` 问答 / `concession` 让步 / `conclusion`
  因果（硬约束，不得切开）与 `echo` 蝉联 / `ref_chain` 指代（软约束，优先同拍）。
  `beat_planner` 全量重写接入硬/软约束 + `HARD_CEIL = MAX_D × 1.75` 绝对上限；
  每拍附带 `semantic_pairs`（拍内关系）与 `out_relations`（跨拍关系）供导演层
  选策略与做透明化审计。
- **语义策略提示**（`visual_director`）：问答/因果对同拍 → `cause_effect`，
  让步对同拍 → `comparison`。优先级：显式覆写 > 数字编码 > 特色角色默认 >
  语义提示 > 通用默认；R8 邻拍避让仍生效。
- **self_test 语义门禁**：合成问答/让步/因果 cue 序列，断言硬约束对绝不被
  切开、`semantic_pairs` 落位、硬约束组不超 `HARD_CEIL`。

### Fixed

- 用户反馈「断句断得很生涩完全没有逻辑」：纯时长贪心把「你要的到底是什么 →
  你说是赢」「铺垫 → 可…」这类语义对从中间撕开。v4.3 起这类对强制同拍。

版本号语义：`主版本.次版本.修订`。
- 主版本：中间产物 Schema 出现破坏性变更（删字段/改语义）；
- 次版本：新增技能模块、新构图模板、新事件动作等新能力；
- 修订：文档修订、bug 修复、门禁阈值微调。

## [4.2.1] — 2026-10-03

### Removed

- **移除全片常驻 corner_marks 画框**：用户反馈其像摄像取景框、无装饰价值。
  为只剩 1 件装饰的策略（flow/cause/comparison/before_after）各补一件
  低调氛围装饰（tick_line/dot_grid），维持每拍 ≥2 个 decor 的门禁。
  `svg_art.corner_marks` 画法保留在库中备用，默认不再生成。

## [4.2.0] — 2026-10-03

### Added

- **cinema 电影感暗色主题**（`common.THEME`）：纵向渐变底 + 径向暗角 +
  胶片颗粒 + 遮幅黑边；PIL 渲染器与 HTML 播放器共用同一份主题常量
  （双侧一致）。
- **排版主角化**：标题/关键词/金句/数字走衬线大字（Noto Serif CJK），
  强调元素带同色系柔光（shadowBlur），eyebrow 加字距。
- **motif 水印化**：单 motif 放大 2.2×、透明度 0.15 垫在文字之下；
  多 motif 对照保持构图盒子、透明度 0.55。

### Changed

- boxed 圆角描边框 → 上下细金线（accent rule）；shape 面板 → 径向光晕。
- 遮幅 0.055 → 0.04（避免盖住 36px 处的 corner_marks 画框）。
- `ink_stats` 裁掉遮幅、以主题底色为基准（暗色主题下的 L3 探针适配）。
- 用户反馈驱动：v4.1 米色信息图风格被评价为「画面好丑」，v4.2 视觉层
  整体重做；导演层 / 构图 / 编排逻辑不变（视觉是渲染层政策）。

## [4.1.0] — 2026-10-03

### Added

- **SVG 画法库** `runtime/svg_art.py`：5 种非拟人主体画法（phone/moon/shield/
  clock/alert）+ 5 种装饰附体画法（corner_marks/ring_pair/dot_grid/tick_line/
  divider），矢量定义、`audit_svg` 越界机器门禁、cairosvg 光栅化带 LRU 缓存；
  PIL 渲染器与 HTML 播放器共用同一份 SVG 字符串（双侧实现 = 同一幅画）。
- **装饰附体层（decor）**：每拍 2-3 个 ambient 装饰元素（自带归一化 rect、
  不参与模板区域预算）；`corner_marks` 画框自第 2 拍起常驻（连续性基底）；
  幽灵大字（特大号低透明度关键词垫在主体之下，强调的环境回声，EMP-06）。
- **每元素生命周期**：entrance-plan 以 `lifecycle` 为时序真值——
  enter{at,motion,dur,after} + exit{at,motion,dur}|null；`after` 声明
  「等谁建立之后才出现」的依赖（CHOR-12）；cue 序列降级为 lifecycle 的派生视图。
- **跨拍连续**：拍首 0.45s 旧场景溶解退出（PIL 渲染器与 HTML 播放器同语义）；
  交接主体 enter.motion=inherit（不重新入场）+ 跨拍位置插值（CHOR-15）。
- 新门禁：构图 `GATE-A20`（接近性 ≤0.28 对角线）/ `GATE-A21`（视觉平衡
  ≥0.30）；编排 `GATE-G5`（生命周期完整性）；L1 校验新增 lifecycle 覆盖检查。
- `runtime/render_video.py`：可选 MP4 导出（imageio-ffmpeg 自带静态 ffmpeg）。

### Changed

- motif 词汇表**去拟人化**：移除 person，文字/图形/图表都可以当画面主体
  （FORM-01）。
- `GATE-G2` 波次间隔从「拍长 8%」改为绝对值 `G_MIN_WAVE_GAP = 0.25s`。
- 入场 motion 词表新增 `inherit`；退场词表 fade/sink/shrink 落地双侧渲染。
- self_test 扩充：SVG 画法审计、非拟人校验、decor ≥2、lifecycle 断言、
  合成交接链测试（8 道门禁全 PASS）。

## [4.0.0] — 2026-10-03

### Changed（载体重组，方法论不变）

- 将 v3.0 单文档（~6900 行）重组为 `skills/` 下 **11 个模块技能 +
  主协调器** `skills/coordinator.md`：拆分原则为「一个模块只回答一类问题」。
- 规则编号体系重建：废弃原文档重叠的章节号（如 §10.16 曾出现两次），
  改用全仓库唯一的主题编号（`CORE-nn` / `SRT-nn` / `BEAT-nn` / `GATE-Rn` /
  `GATE-Gn` / `CHOR-nn` / `DSL-nn` …），编号只增不改、不随文档重组变化。
- 清理全部版本残留表述（「此前版本＿＿」式悬空指代）。
- 规则分级：[强制] / [经验] / [建议] 三级；只有 [强制] 级进入 CI 与
  `runtime/self_test.py`。

### Added

- **可运行参考 Runtime**（`runtime/`，Pillow + jsonschema 单依赖）：
  `srt_parser` / `beat_planner` / `visual_director` / `composition_planner` /
  `entrance_planner` / `raster_renderer` / `html_adapter` / `validator` /
  `pipeline` / `make_sample` / `self_test` / `common`。
- `runtime/self_test.py`：8 道 Bootstrap 门禁（SRT 解析 → Beat 覆盖 →
  导演层 R8 → 构图拒猜坐标 → 入场 G 门禁 → L3 光栅探针 → HTML 适配器 →
  30s 端到端），当前全部 PASS。
- 6 个中间产物的 JSON Schema（`schemas/`）。
- 最小示例 `examples/minimal/`：8 条字幕 / 38 秒，覆盖 5 种构图模板与
  2 种数字编码（donut / bars），附导演覆写示例。
- 自包含 HTML5 Canvas 播放器适配器（`film/index.html`，编译产物只读）。
- L3 光栅探针：每拍拍尾真实帧 + 墨水量/颜色数机器事实。
- GitHub 配套：CI（`.github/workflows/self_test.yml`）、README、
  CONTRIBUTING、ROADMAP、LICENSE(MIT)、.gitignore。

### Known limits（诚实声明）

- 参考 Runtime 是最小基线：6 套模板 / 4 种 motif / 2 种图表 /
  1 种镜头运动；扩展方式见 CONTRIBUTING。
- L4（语义/审美）不可自动化，`validation-report.json` 中恒为 PENDING。
- 不含 ffmpeg；样例产物为 PNG 帧 + HTML 播放器。
