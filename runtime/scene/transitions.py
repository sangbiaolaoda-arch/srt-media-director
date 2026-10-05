"""Semantic Transition — 语义迁移（Phase 2 · 第四优先级）。

不同状态之间应是「语义变化」，不是让 Agent 手算
x/y、transition-duration、delay。这里提供可链式调用的语义迁移构造器，
最终 to_motion() 交给 Motion Compiler 变成动画参数。
"""
from __future__ import annotations

from . import motion_compiler as MC

# 语义迁移动词库（§5）
VERBS = ("expand", "collapse", "appear", "disappear", "grow", "shrink",
         "split", "merge", "separate", "connect", "disconnect", "surround",
         "reveal", "conceal", "emphasize", "deemphasize", "follow",
         "transform", "morph", "stagger", "compress", "scatter", "focus")


class Transition:
    def __init__(self, frm, to):
        self.frm = frm
        self.to = to
        self.actions = []          # [(verb, {opts})]

    def _add(self, verb, **opts):
        self.actions.append((verb, opts))
        return self

    def expand(self, target=None, **o):    return self._add("expand", target=target, **o)
    def collapse(self, target=None, **o):  return self._add("collapse", target=target, **o)
    def appear(self, target=None, **o):    return self._add("appear", target=target, **o)
    def disappear(self, target=None, **o): return self._add("disappear", target=target, **o)
    def grow(self, target=None, **o):      return self._add("grow", target=target, **o)
    def shrink(self, target=None, **o):    return self._add("shrink", target=target, **o)
    def split(self, target=None, **o):     return self._add("split", target=target, **o)
    def merge(self, target=None, **o):     return self._add("merge", target=target, **o)
    def surround(self, target=None, **o):  return self._add("surround", target=target, **o)
    def reveal(self, target=None, **o):    return self._add("reveal", target=target, **o)
    def morph(self, target=None, **o):     return self._add("morph", target=target, **o)
    def stagger(self, target=None, **o):   return self._add("stagger", target=target, **o)
    def compress(self, target=None, **o):  return self._add("compress", target=target, **o)
    def scatter(self, target=None, **o):   return self._add("scatter", target=target, **o)
    def focus(self, target=None, **o):     return self._add("focus", target=target, **o)

    def to_motion(self):
        """编译为动画意图；stagger/compress 等无基础动作的迁移转为节奏参数。"""
        motions = []
        rhythm = {}
        for verb, opts in self.actions:
            if verb in MC.SEMANTIC_ACTIONS:
                m = MC.compile_action(verb, **{k: v for k, v in opts.items()
                                               if k != "target"})
                if opts.get("target"):
                    m["target"] = opts["target"]
                motions.append(m)
            else:
                rhythm[verb] = opts
        return {"from": self.frm, "to": self.to, "motions": motions,
                "rhythm": rhythm}

    def to_dict(self):
        return {"from": self.frm, "to": self.to, "actions": self.actions}
