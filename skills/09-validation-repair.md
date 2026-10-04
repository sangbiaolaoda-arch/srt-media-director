# 09 · 分层验证与修复协议（Validation & Repair）

> 阶段产物：`validation-report.json`（+ 修复时的 `repair-log.json`）
> 参考实现：`runtime/validator.py` · `runtime/self_test.py`
> 约束：CORE-11 / CORE-12 / CORE-08 / CORE-14

## 1. 四层验证，各管各的

| 层 | 名称 | 检查什么 | 执行者 | 何时跑 |
|---|---|---|---|---|
| L1 | Machine | 跨文件一致性：beat 覆盖完整、id 链对齐、时间正向、primary 恰 1、host/relation 不悬空、claim/evidence 存在 | 机器 | 每次编译后 |
| L2 | Layout / Static | 布局门禁 R1-R8 / A15 / A19 / A20 / A21；编排门禁 G1-G5 | 机器 | 构图/入场求解时（fail-fast） |
| L3 | Raster / Motion | 对**真实渲染帧**的机器探针：墨水量、颜色数、元素确实出现 | 机器 | 每次编译后（preview/） |
| L4 | Semantic / Visual | 命题是否成立、隐喻是否误导、画面是否好看、是否真的不 PPT | **AI/人工** | 样例确认时 |

- **VAL-01 [强制]** L4 不能由机器伪造。参考实现的 `validation-report.json`
  里 L4 恒为 `PENDING`，直到人或 Agent 看过样例帧并在
  `review-report.json` 里给出结论。「机器全过」不等于「可以交付」。
- **VAL-02 [强制]** L1/L2/L3 任一 FAIL，流水线必须停止并报告；
  禁止「先渲染完再说」。

## 2. L3 光栅探针的机器事实

参考实现（`runtime/raster_renderer.py`）对每拍取「拍尾 93%」处的真实帧
（入场与 resolve 事件均已完成），计算：

- `ink_ratio` ∈ [0.005, 0.65]：下限抓「空帧」（元素没画出来），上限抓
  「塞满」（违反 R7 墨留白）；
- `distinct_colors` ≥ 12：抓「静默回退」（画法崩了只剩基础几何——
  产物「只是看起来简单」，没有探针永远查不出来）。

## 3. 修复路由表（CORE-08 的可执行形式）

| 症状 | 错误层 | 修哪 | 禁止 |
|---|---|---|---|
| 拍切得语义断裂 | Beat | `01` 层规则 / overrides | 在 DSL 层硬凑 |
| 命题不成立、隐喻误导 | Visual Plan | `04` 层 claim/evidence | 改文案迎合画面 |
| 文字压图 / 出安全区 | Composition | Blueprint 区域或文案长度 | 手改 render-plan 坐标 |
| 元素没出现 / 空帧 | Runtime/Adapter | 渲染器画法 | 改 DSL 绕开 |
| 尾段空窗 | Choreography | cue 波次 / hold_reason | 塞无意义动画 |
| 邻拍同模板 | Director | 策略选择（R8 轮换或覆写） | 无视 |

- **REP-01 [强制]** 每次修复写入 `repair-log.json`：症状 → 判定的层 →
  改动 → 重新验证结果。修复历史是项目的审计资产。
- **REP-02 [强制]** 修任何一拍都改上游层重新编译，不直接改编译产物
  （CORE-07）。

## 4. Runtime 自检（Bootstrap Gate）

- **VAL-03 [强制]** Runtime 可以由 Agent 创建，但**不得由它自己宣布正确**。
  `runtime/self_test.py` 是机器证据：20 道门禁覆盖
  SRT 解析 → Beat → 导演层 → 构图（含拒绝猜坐标）→ 入场编排 →
  光栅探针 → HTML 适配器 → 端到端 30s 样例。
  改过 Runtime 任何一行，必须重跑到 VERIFIED 才允许进入正式生产。
- **VAL-04 [强制]** 能力探针纪律：未知 Runtime 能力、未知渲染器 API、
  不存在的素材、未验证的字体/图表能力——只有「找等价实现 / 简化表达 /
  阻断报告」三条路（CORE-14）。

## 5. CI 门禁

`.github/workflows/self_test.yml` 在每次 push 跑
`python runtime/self_test.py`。新增 `[强制]` 级规则时，必须同时在
self_test 或 validator 中给出机器检查——否则这条规则没有牙齿
（见 `CONTRIBUTING.md`）。
