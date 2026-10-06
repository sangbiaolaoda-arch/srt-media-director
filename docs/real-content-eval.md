# Real Content Evaluation (P0)

在真实 SRT 语料上验证 **Production Path Canonical 收敛** 的行为正确性。

## 目的

证明收敛后的生产链（`pipeline.py` → `entrance_planner` → `motion_canonical.entrance`）
在真实内容上与收敛前 **字节级等价**，且产物 **schema 合法**、渲染器可识别。

## 工具

- `tools/equivalence_probe.py` — 对每份真实 SRT：跑完整生产层，比较
  `legacy(HEAD).plan/audit` 与 `canonical(委托后).plan/audit`。
- `tools/real_content_eval.py` — 对每份真实 SRT：跑完整生产层，计算机器指标
  （ink ratio / distinct colors / beat 数 / lint），渲染每拍定格帧，合成联系表。

## 结果（`docs/real-content-eval.json`）

- 11 份真实 SRT（examples/minimal、examples/run×3、examples/showcase×4、
  tests/golden×2、tests/known-failures×1）
- **11/11** layout audit `PASS`、entrance audit `PASS`、entrance-plan schema 合法、
  **0** 非法 motion token（无 `carry_over` / `fade_out` 泄漏）
- **11/11** `legacy == canonical`（plan 与 audit 逐份字节级等价）

## 复现

```
cd runtime && python ../tools/real_content_eval.py
python ../tools/equivalence_probe.py
```

## 诚实边界

本评估证明的是 **行为保持（零漂移收敛）**，不是 **画质提升**。画质/构图的人工评分
（contact sheet 人工打分）尚未执行，故本仓库**不声称本次改动提升成片质量**。
