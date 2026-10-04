"""schemas — 中间语言 JSON Schema（单一真值）。

    visual_intent.json   Agent 产出（语义，零坐标）
    visual_plan.json     导演层产物
    render_plan.json     编译层产物（几何）
"""
import os


def path(name):
    """取某个 schema 的绝对路径。name 可为 'visual_intent' 等。"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".json")


def load(name):
    import json
    with open(path(name), encoding="utf-8") as f:
        return json.load(f)


def available():
    return [os.path.splitext(f)[0] for f in sorted(os.listdir(os.path.dirname(os.path.abspath(__file__))))
            if f.endswith(".json")]
