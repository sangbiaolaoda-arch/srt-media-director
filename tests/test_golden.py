"""黄金回归测试：固定 SRT → 各层中间产物哈希比对。

声明支撑：项目声称「种子取自拍号 + 字幕，跨机器可复现」。这条声明必须
有回归测试兜底，否则不可信。

关键：**归一化后再哈希**。直接哈希原始 JSON 会因为时间戳、主机名、耗时、
绝对路径等 volatile 字段而永远对不上。归一化步骤：

    原始 JSON
      → 递归删除 volatile 键（generated_at / host / elapsed_ms / path ...）
      → sort_keys + 固定缩进
      → utf-8 + LF
      → sha256

用法：
    pytest tests -q                      # 校验（CI 默认）
    UPDATE_GOLDEN=1 pytest tests -q      # 重新生成基准（本地，人工确认后提交）
"""
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")

# 归一化时剔除的 volatile 键（值随机器/时间变化，不该参与哈希）
VOLATILE_KEYS = {
    "generated_at", "created_at", "timestamp", "host", "hostname",
    "elapsed_ms", "duration_ms", "runtime_ms", "abs_path", "path",
    "project_root", "out_dir", "tool_version", "cwd", "user",
}

# 参与回归的五层产物 + 顺序（依赖顺序，先算前层）
LAYERS = [
    "beat-plan.json",
    "visual-plan.json",
    "visual-dsl.json",
    "render-plan.json",
    "entrance-plan.json",
]


def _normalize(obj):
    """递归清理 volatile 键，返回可稳定序列化的结构。"""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in sorted(obj.items())
                if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        # 浮点末位在不同平台可能差 1ulp；固定到 6 位小数
        return round(obj, 6)
    return obj


def _hash_artifact(path):
    doc = json.load(open(path, encoding="utf-8"))
    payload = json.dumps(_normalize(doc), sort_keys=True, ensure_ascii=False,
                         indent=2, separators=(",", ": ")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _cases():
    if not os.path.isdir(GOLDEN_DIR):
        return []
    out = []
    for name in sorted(os.listdir(GOLDEN_DIR)):
        d = os.path.join(GOLDEN_DIR, name)
        srt = os.path.join(d, "case.srt")
        if os.path.isdir(d) and os.path.exists(srt):
            out.append((name, d, srt))
    return out


CASES = _cases()
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"


@pytest.mark.parametrize("name,gdir,srt", CASES, ids=[c[0] for c in CASES])
def test_golden_hashes(name, gdir, srt, tmp_path):
    import pipeline

    out = str(tmp_path / "out")
    # 只编译、不渲染：黄金测试盯的是中间语言层的确定性，不是像素
    pipeline.run(srt, out, render_previews=False, log=lambda *a: None)

    work = os.path.join(out, "work")
    got = {layer: _hash_artifact(os.path.join(work, layer)) for layer in LAYERS}

    hpath = os.path.join(gdir, "hashes.json")
    if UPDATE or not os.path.exists(hpath):
        if not UPDATE:
            pytest.skip("no baseline yet; run UPDATE_GOLDEN=1 to create")
        json.dump(got, open(hpath, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        return

    want = json.load(open(hpath, encoding="utf-8"))
    mismatches = [l for l in LAYERS if got.get(l) != want.get(l)]
    assert not mismatches, (
        "golden layer(s) changed: %s\n"
        "若为有意的产物变更，请人工确认后 UPDATE_GOLDEN=1 重生成基准。"
        % ", ".join(mismatches))
