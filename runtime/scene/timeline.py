"""Timeline Graph — 时间关系（Phase 2 · 第五优先级）。

解决「元素都有动画，但没有明确出现逻辑」。每个入场/动作节点带时间关系：
before / after / with / overlap / delay / stagger / follow。

调度算法：按依赖做拓扑排序，给每个节点一个 start 时刻；stagger 是「同组内
相对前一个 +step」；overlap 是「与前一个重叠 overlap 秒」。
"""
from __future__ import annotations

REL = ("before", "after", "with", "overlap", "delay", "stagger", "follow")


class TimelineGraph:
    def __init__(self):
        self.entries = {}   # key -> {action, target, rel, anchor, offset, dur}

    def add(self, key, action, target=None, after=None, before=None, with_=None,
            overlap=None, delay=None, stagger=None, follow=None, dur=0.5,
            duration=None):
        if duration is not None:
            dur = duration
        e = {"key": key, "action": action, "target": target, "dur": dur,
             "rel": None, "anchor": None, "offset": 0.0}
        if after is not None:
            e["rel"], e["anchor"] = "after", after
        elif before is not None:
            e["rel"], e["anchor"] = "before", before
        elif with_ is not None:
            e["rel"], e["anchor"] = "with", with_
        elif follow is not None:
            e["rel"], e["anchor"] = "follow", follow
        if overlap is not None:
            e["rel"], e["offset"] = "overlap", float(overlap)
            e["anchor"] = after
        if delay is not None:
            e["rel"], e["offset"] = "delay", float(delay)
            e["anchor"] = after
        if stagger is not None:
            e["rel"], e["offset"] = "stagger", float(stagger)
            e["anchor"] = after
        self.entries[key] = e
        return e

    def schedule(self, base=0.0):
        """拓扑调度，返回 key -> {start, dur, end}。"""
        start = {}
        visiting = set()

        def resolve(key, stack=()):
            if key in start:
                return start[key]
            if key in stack:
                # 环：回退为 base
                return base
            e = self.entries[key]
            anchor = e["anchor"]
            if anchor is None or anchor not in self.entries:
                s = base
            else:
                resolve(anchor, stack + (key,))
                a = start[anchor]
                rel = e["rel"]
                if rel == "after":
                    s = a["end"]
                elif rel == "before":
                    s = a["start"] - e["dur"]
                elif rel == "with":
                    s = a["start"]
                elif rel == "follow":
                    s = a["end"] + 0.0
                elif rel == "overlap":
                    s = a["end"] - e["offset"]
                elif rel == "delay":
                    s = a["end"] + e["offset"]
                elif rel == "stagger":
                    s = a["start"] + e["offset"]
                else:
                    s = a["end"]
            start[key] = {"start": round(s, 4), "dur": e["dur"],
                          "end": round(s + e["dur"], 4)}
            return start[key]

        for k in self.entries:
            resolve(k)
        return start

    def audit(self):
        issues = []
        for k, e in self.entries.items():
            if e["anchor"] and e["anchor"] not in self.entries:
                issues.append({"severity": "err", "code": "TIMELINE_DANGLING",
                               "msg": "entry %r anchors missing %r" % (k, e["anchor"])})
        # 同时刻并发告警
        sched = self.schedule()
        starts = {}
        for k, v in sched.items():
            starts.setdefault(round(v["start"], 2), []).append(k)
        for t, ks in starts.items():
            if len(ks) >= 3:
                issues.append({"severity": "warn", "code": "TIMELINE_SIMULTANEOUS",
                               "msg": "%d entries start together at %.2f: %s"
                                      % (len(ks), t, ks)})
        return {"status": "FAIL" if any(i["severity"] == "err" for i in issues)
                else "PASS", "issues": issues, "schedule": sched}

    def to_dict(self):
        return {"entries": self.entries, "schedule": self.schedule()}
