"""SVG 光栅化后端抽象 —— 主路径 cairosvg，缺失时降级。

设计动机（P3-8）：cairosvg 依赖系统 cairo / GTK，是这类渲染管线跨平台
最常见的失败点。后端必须**可切换**且**降级不崩**：

    1. cairosvg  —— 首选（矢量精度高，支持滤镜/裁剪）
    2. resvg     —— 备用（Rust 实现，静态二进制，无系统 cairo 依赖）
    3. none      —— 无可用后端时返回明确状态，让上层决定「简化表达 or 阻断」，
                    绝不静默伪装成「已渲染」。

用法：
    python runtime/svg_backend.py --probe     # 打印可用后端与版本（CI 用）
"""
import argparse
import json
import shutil
import sys


def _try_cairosvg():
    try:
        import cairosvg
        # 触发一次真实渲染，确认系统 cairo 真的可用（import 成功不代表能渲染）
        cairosvg.svg2png(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" '
                                   b'width="8" height="8"><rect width="8" '
                                   b'height="8" fill="#f4efe6"/></svg>')
        return {"name": "cairosvg", "available": True,
                "version": getattr(cairosvg, "__version__", "unknown")}
    except Exception as e:  # noqa: BLE001 — 任何失败都归为不可用
        return {"name": "cairosvg", "available": False, "error": str(e)[:160]}


def _try_resvg():
    exe = shutil.which("resvg")
    if not exe:
        return {"name": "resvg", "available": False, "error": "resvg not on PATH"}
    import subprocess
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                             timeout=10)
        return {"name": "resvg", "available": out.returncode == 0,
                "version": (out.stdout or out.stderr).strip()[:40]}
    except Exception as e:  # noqa: BLE001
        return {"name": "resvg", "available": False, "error": str(e)[:160]}


def probe():
    """返回后端清单与选中的后端。选择顺序 cairosvg → resvg。"""
    backends = [_try_cairosvg(), _try_resvg()]
    chosen = next((b["name"] for b in backends if b["available"]), None)
    return {"backends": backends, "chosen": chosen,
            "degraded": chosen is None}


def main():
    ap = argparse.ArgumentParser(prog="svg_backend")
    ap.add_argument("--probe", action="store_true",
                    help="打印后端可用性（CI 降级验证用）")
    args = ap.parse_args()
    if args.probe:
        result = probe()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # 关键：降级本身不算失败——CI 的 svg-fallback job 就是要证明
        # 「无系统 cairo 时优雅降级」而非崩溃。始终 exit 0。
        sys.exit(0)
    ap.print_help()


if __name__ == "__main__":
    main()
