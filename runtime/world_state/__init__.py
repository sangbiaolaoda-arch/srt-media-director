"""Phase 0 world-state package: model + serializer + compiler + validator.

This is the browser-free core of the Falsifiability-First loop:

    Anchor --(Entailment Contract)--> Expected --(Runtime)--> WorldState --> Verdict
"""
from .model import Frame, Obj, Relation, WorldState
from . import compiler, serializer, validator

__all__ = [
    "Obj", "Relation", "Frame", "WorldState",
    "serializer", "compiler", "validator",
]
