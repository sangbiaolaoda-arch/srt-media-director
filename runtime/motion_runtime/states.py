"""runtime/motion_runtime/states.py — State Graph（Runtime Hardening · P0）。

对象不能只有 visible / hidden。必须允许：

    inactive → activating → active → strengthening → dominant
             → weakening → blocked → waiting → resolved

每个 State Transition 必须明确：trigger / guard / from_state / to_state /
duration / interrupt / rollback。

**任何状态变化都必须拥有原因；禁止无原因的突然变化。**
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

STATES = ("inactive", "activating", "active", "strengthening", "dominant",
          "weakening", "blocked", "waiting", "resolved")

Guards = Callable[[dict], bool]


@dataclass
class StateTransition:
    from_state: str
    to_state: str
    trigger: str
    guard: Optional[str] = None
    duration: float = 0.3
    interrupt: bool = True
    rollback: Optional[str] = None
    reason: Optional[str] = None

    def validate(self) -> List[str]:
        errs = []
        if self.from_state not in STATES:
            errs.append("bad from_state: %s" % self.from_state)
        if self.to_state not in STATES:
            errs.append("bad to_state: %s" % self.to_state)
        if not self.trigger:
            errs.append("state transition requires trigger (no reason -> forbidden)")
        if self.guard is not None and not isinstance(self.guard, str):
            errs.append("guard must be a named predicate")
        if self.duration < 0:
            errs.append("duration must be >= 0")
        if self.rollback is not None and self.rollback not in STATES:
            errs.append("bad rollback state: %s" % self.rollback)
        return errs

    def to_dict(self) -> dict:
        return {"from_state": self.from_state, "to_state": self.to_state,
                "trigger": self.trigger, "guard": self.guard,
                "duration": self.duration, "interrupt": self.interrupt,
                "rollback": self.rollback, "reason": self.reason}


class StateRuntime:
    """带守卫（guard）的状态机。无 trigger 的转移被禁止。"""

    def __init__(self):
        self._state: Dict[str, str] = {}
        self._transitions: List[StateTransition] = []
        self._guards: Dict[str, Guards] = {}
        self._history: List[dict] = []

    # ---------------------------------------------------------- 配置
    def register_guard(self, name: str, fn: Guards) -> None:
        self._guards[name] = fn

    def add_transition(self, tr: StateTransition) -> None:
        errs = tr.validate()
        if errs:
            raise ValueError("invalid transition: %s" % "; ".join(errs))
        self._transitions.append(tr)

    def initial(self, nid: str, state: str = "inactive") -> None:
        if state not in STATES:
            raise ValueError("bad state: %s" % state)
        self._state[nid] = state

    # ---------------------------------------------------------- 查询
    def state_of(self, nid: str) -> str:
        return self._state.get(nid, "inactive")

    def can(self, nid: str, trigger: str, ctx: Optional[dict] = None) -> bool:
        cur = self.state_of(nid)
        for tr in self._transitions:
            if tr.from_state == cur and tr.trigger == trigger:
                if tr.guard is None:
                    return True
                g = self._guards.get(tr.guard)
                return bool(g(ctx or {})) if g else False
        return False

    # ---------------------------------------------------------- 触发
    def fire(self, nid: str, trigger: str, ctx: Optional[dict] = None) -> Optional[StateTransition]:
        cur = self.state_of(nid)
        for tr in self._transitions:
            if tr.from_state != cur or tr.trigger != trigger:
                continue
            if tr.guard is not None:
                g = self._guards.get(tr.guard)
                if not (g and g(ctx or {})):
                    continue
            self._state[nid] = tr.to_state
            self._history.append({"node": nid, "from": tr.from_state,
                                  "to": tr.to_state, "trigger": trigger,
                                  "guard": tr.guard})
            return tr
        return None

    @property
    def history(self) -> List[dict]:
        return list(self._history)

    def default_chain(self) -> None:
        """注册常用链路：inactive→activating→active→strengthening→dominant。"""
        chain = [("inactive", "activating", "activate"),
                 ("activating", "active", "complete"),
                 ("active", "strengthening", "reinforce"),
                 ("strengthening", "dominant", "dominate"),
                 ("active", "weakening", "fade"),
                 ("strengthening", "weakening", "fade"),
                 ("dominant", "weakening", "fade"),
                 ("weakening", "inactive", "deactivate"),
                 ("active", "resolved", "resolve")]
        for fr, to, trig in chain:
            self._transitions.append(StateTransition(fr, to, trig))

    def audit(self) -> dict:
        issues = []
        for tr in self._transitions:
            for e in tr.validate():
                issues.append({"transition": "%s->%s" % (tr.from_state, tr.to_state),
                               "error": e})
        # 每个节点当前状态必须可达（非空）
        for nid in self._state:
            if self._state[nid] not in STATES:
                issues.append({"node": nid, "error": "illegal state"})
        return {"status": "FAIL" if issues else "PASS",
                "states_tracked": len(self._state),
                "transitions": len(self._transitions), "issues": issues}
