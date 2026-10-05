"""runtime/motion_runtime — Runtime Hardening: Motion Primitive Runtime.

语义运动执行层：关系产生运动 / 状态驱动运动 / 事件驱动时间 / 约束决定空间 /
Camera 管理注意力 / Runtime 执行运动 / Validator 保证正确。

公共入口：
    MotionRuntime              执行系统集成
    MotionPrimitive / make     语义运动原语
    PRIMITIVES / PRIMITIVE_TYPES
    SceneGraph / Node          场景图（层级隶属）
    RelationRuntime / Relation 关系运行时（谁影响谁）
    StateRuntime               状态图（守卫转移）
    ConflictSolver             运动冲突求解
    ConnectorRuntime           动态连接线
    Camera                     Camera / 注意力
    EventGraph                 事件/时间线图
    IdentityRegistry           稳定身份
    run_all / invariants       Motion Invariants
"""
from .camera import Camera, attention_sequence
from .conflict import ConflictSolver, Contribution, BLEND_MODES
from .connector import ConnectorRuntime, DynamicConnector
from .contracts import (MotionContract, MotionPrimitive, PRIMITIVES, PRIMITIVE_TYPES,
                        PrimitiveDef, SceneCtx, CHANNELS, CHANNEL_NEUTRAL, EASINGS,
                        audit_contracts, make)
from .events import Event, EventGraph, dependency, parallel, sequence, stagger
from .identity import IdentityRegistry, check_identity_continuity
from .invariants import run_all
from .relations import Relation, RelationRuntime, RELATION_TYPES, PHASES
from .runtime import MotionRuntime
from .scene import Node, SceneGraph
from .states import StateRuntime, StateTransition, STATES

__all__ = [
    "MotionRuntime", "MotionPrimitive", "MotionContract", "PrimitiveDef", "make",
    "PRIMITIVES", "PRIMITIVE_TYPES", "SceneCtx", "CHANNELS", "CHANNEL_NEUTRAL",
    "EASINGS", "audit_contracts",
    "SceneGraph", "Node", "RelationRuntime", "Relation", "RELATION_TYPES", "PHASES",
    "StateRuntime", "StateTransition", "STATES", "ConflictSolver", "Contribution",
    "BLEND_MODES", "ConnectorRuntime", "DynamicConnector", "Camera", "attention_sequence",
    "EventGraph", "Event", "sequence", "parallel", "stagger", "dependency",
    "IdentityRegistry", "check_identity_continuity", "run_all",
]
