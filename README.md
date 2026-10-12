# SRT Media Director

> 把 SRT 字幕变成有导演思维的信息图动画：不是「字幕 → PPT」，
> 而是「语言理解 → 视觉命题 → 强调与编码 → 构图 → 时序编排 → 可验证渲染」。

[![ci](https://github.com/sangbiaolaoda-arch/srt-media-director/actions/workflows/ci.yml/badge.svg)](https://github.com/sangbiaolaoda-arch/srt-media-director/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)

## 一句话

给 Agent 一段 SRT，它输出：`beat-plan → visual-plan → visual-dsl →
render-plan → entrance-plan → film/index.html（可播放）→
validation-report（机器证据）`——每一层落盘、每一层可校验、
每一层错误都有明确的修复路由。

> **v7.3 起**：Agent 只输出**视觉意图**（Visual Claim / Grammar / Focal Point /
> Relationship Graph / Density / Silence / Motion Intent），几何由 Runtime 的
> 构图编译器决定——Agent 不再「选模板」、不再「猜像素」。见
> [`skills/14-intent-layer.md`](skills/14-intent-layer.md)。

> **v7.4 起**：Runtime 拆为职责清晰的六包
> （`director/ compiler/ render/ validation/ primitives/ schemas/`），并落地
> **生成 → 截图 → Critic → 修复** 闭环：每生成一个 Beat 就自动截图，交给机器
> Critic，PASS 才前进，FAIL 就带修复目标层回到上游重编重截。见
> [`skills/15-runtime-architecture.md`](skills/15-runtime-architecture.md)。

## 排版库（110 套构图蓝图）

「反 PPT」的核心不是堆特效，而是**构图词汇的厚度**。项目内置 110 套归一化排版
蓝图（[`runtime/capability_library/layout_library.py`](runtime/capability_library/layout_library.py)），
按内容类型分为三族：

| 族 | 数量 | 覆盖 |
|---|---|---|
| 文字 | 42 | 堆叠 / 标题主角 / 双栏·三栏 / 引用金句 / 叠层 / 大数字 |
| 图像 | 34 | 主图配文 / 图文分栏 / 图集 / 满幅 / 竖幅 / 对照 / 画中画 |
| 图表 | 34 | 环形 / 柱状（横竖） / 折线 / KPI 行 / 散点 / 瀑布 |

每套蓝图是**归一化区域图**（坐标 0–1，安全区 0.07），与渲染器解耦：
导演层可直接引用，也可单独在浏览器预览——不是截图，是可复现的构图语法。

**全览 · 25 套代表**

![layout overview](examples/layout-gallery/overview.svg)

**文字排版 · 42 套**

![text layouts](examples/layout-gallery/text.svg)

**图像排版 · 34 套**

![image layouts](examples/layout-gallery/image.svg)

**图表排版 · 34 套**

![chart layouts](examples/layout-gallery/chart.svg)

> 每张卡片：圆角框 = 区域槽位，角标数字 = 阅读顺序，左上角 = 蓝图 id / 族。

复现画廊（进入 `runtime/` 目录，仅依赖标准库）：
```bash
python -m capability_library.render_gallery --out ../examples/layout-gallery
```

契约门禁：
```bash
python -m pytest tests/phase0/test_capability_library.py -q   # 17 项
```

配套能力：**50 套 GSAP 入场**（`entrance_library.py`）与 **50 套元素动态关系**
（`relation_library.py`），编译成浏览器可用包：
```bash
python -m capability_library.gsap_emit --out capability_library/dist
```

## 快速开始

```bash
pip install pillow jsonschema cairosvg
python runtime/self_test.py        # Bootstrap Gate：25 道门禁
python cli.py examples/minimal/attention.srt \
  --out sample --overrides examples/minimal/director_overrides.json
```

打开 `sample/film/index.html` 即可播放；`sample/sheet.jpg` 是全部拍的
联系表拼图；`sample/work/` 里是所有中间层 JSON。

调试画面时走样例优先工作流（不要直接渲全片）：

```bash
python runtime/make_sample.py 30              # 前 30 秒全流程 + 拼图
python runtime/make_sample.py 30 --no-render  # 只编译 + 门禁（2 秒级）
```

## 这套方法论解决什么

| 常见做法 | 本项目的替代 |
|---|---|
| 字幕逐句放大 | 每拍一句 Visual Claim，遮住字幕画面仍能传达命题 |
| 素材驱动（有什么贴什么） | 命题驱动：先决定表达什么，再决定素材形态（DSL 是 asset-blind 的） |
| 元素按代码顺序 fade in | 每元素生命周期（enter/exit/after 依赖）+ cue 波次编排：同 cue 真同时、拍尾干净（G5）、跨拍溶解交接 |
| 生成整片再祈祷 | 样例优先（30s）+ 分层验证（L1 机器一致性 / L2 布局门禁 / L3 光栅探针 / L4 人工审美） |
| 编一个 API 让流程继续 | CORE-14：能力缺失只有「等价实现 / 简化 / 阻断报告」三条路 |

## 文档结构（Agent 用法）

- **统筹技能包**：[`skills/coordinator.md`](skills/coordinator.md)——
  Agent 先读它，按阶段调用表加载单个模块，避免上下文过载。
- **模块技能**：[`skills/`](skills/README.md) 下 11 个主题文档，
  规则带唯一编号（`CORE-nn` / `GATE-R8` …），修复日志按编号引用。
- **参考 Runtime**：[`runtime/`](runtime/)——Pillow 单依赖，
  `self_test.py` 是可执行的规格说明。
- **契约 Schema**：[`schemas/`](schemas/)——6 个中间产物的
  JSON Schema，validator 逐层校验。

## 设计哲学（六条）

1. 内容驱动，而不是素材驱动。
2. 关系优先，而不是元素数量优先。
3. 层级优先，而不是平均分布（每拍恰好一个 primary）。
4. 状态变化优先，而不是动作数量优先（Fade In 不算动画）。
5. 连续性优先于特效（先回答「为什么 A 变成 B」）。
6. 可验证优先于「感觉正确」（机器查错误，人查审美，互不替代）。

## 范围与边界（诚实声明）

- 参考 Runtime 是**最小可运行实现**：6 套构图模板、**24 种非拟人 SVG 主体
  画法 + 16 种装饰附体画法**（`runtime/svg_art.py`，合计 40 种矢量画法）、
  5 套情绪背景调色板、1 种镜头运动。它是「经过验证的基线」，不是功能全集
  ——扩展方式见 `CONTRIBUTING.md`。
- 每拍至少 3 个图形/图表/文字要素；装饰在规则内受控随机（种子 =
  `md5(beat_id + 字幕)`，跨机器可复现），并带 4 拍冷却去重。
- 当前适配器输出**自包含 HTML5 Canvas 播放器**；接入 HyperFrames /
  Remotion 等渲染器时，保留 `skills/` 方法论与中间产物契约即可
  （中间语言与执行器解耦是设计目标）。
- MP4 导出为可选能力：`pip install imageio-ffmpeg`（自带静态 ffmpeg）后
  运行 `python runtime/render_video.py --out out/sample.mp4`；无此依赖时
  样例产物为 PNG 探针帧 + HTML 播放器。
- L4（语义/审美）验证**无法自动化**，`validation-report.json` 中恒为
  PENDING——请真的去看 `preview/` 里的帧。

## 质量门禁与可复现性

本项目把「可验证优先」落到机器可查的指标上，而不是口号：

- **重复感门禁（REP）**：把「画面重复 / 没随机感」变成五个可计算量——
  同一模板连续拍数、模板分布熵、相邻拍相似度（模板/区域/调色板/装饰
  加权和）、调色板占比、装饰复现间隔。阈值分 WARN / FAIL，FAIL 让 L2
  整体不通过。见 [`runtime/rep_metrics.py`](runtime/rep_metrics.py)。
- **黄金回归（golden）**：固定 SRT → 五层中间产物（beat-plan / visual-plan
  / visual-dsl / render-plan / entrance-plan）**归一化后哈希比对**。
  「种子跨机器可复现」的声明由 [`tests/`](tests/) 回归测试支撑——它上线
  第一天就抓到并固化了 `PYTHONHASHSEED` 导致的跨进程漂移（见
  [`known-failures/F03`](examples/known-failures/)）。
- **终端渲染兜底**：`runtime/svg_backend.py` 主用 cairosvg、备选 resvg、
  缺失时明确降级而非静默伪装；CI 的 `svg-fallback` job 专门验证「无系统
  cairo 时优雅降级」。

```bash
python runtime/self_test.py     # 25 道 Bootstrap Gate
python -m pytest tests -q       # 黄金哈希回归
python runtime/svg_backend.py --probe   # SVG 后端可用性
```

## 参与贡献

见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。核心约定：**新增 [强制] 级规则
必须附带机器检查**（self_test 或 validator），没有牙齿的规则不进主干。

## License

[MIT](LICENSE) © SRT Media Director contributors
