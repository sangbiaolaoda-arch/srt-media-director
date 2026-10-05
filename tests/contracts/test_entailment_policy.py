"""Entailment Contract policy tests — Directive v5 §14-§16.

The entailment contract is an AUDITED POLICY, not a runtime rule. These tests
validate the policy's own semantics *without calling the Runtime*:

  * CAUSES(A,B) entails A->B and temporal precedence A before B;
  * CAUSES(A,B) does NOT entail the inverse B->A (direction is not symmetric);
  * every entailment kind is a known, enforced kind (no silent no-op typo).

They read the contract JSON and assert on its content/semantics directly.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENT_DIR = os.path.join(ROOT, "runtime", "entailment")

# kinds the serializer knows how to enforce; a policy entry with any other kind
# would be an unenforced no-op.
KNOWN_HARD = {"relation_direction", "temporal_precedence", "final_focus"}

CONTRACTS = ["causes.v1.json", "follows.v1.json", "connects.v1.json"]


def _contract(name):
    with open(os.path.join(ENT_DIR, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("name", CONTRACTS)
def test_contract_self_declares_independence_and_review(name):
    c = _contract(name)
    assert c["review"]["status"] == "audited"
    assert c["review"]["independent_of_runtime"] is True


@pytest.mark.parametrize("name", CONTRACTS)
def test_every_entailment_kind_is_enforceable(name):
    c = _contract(name)
    assert c["entailment"], "contract must entail something"
    for rule in c["entailment"]:
        assert rule["kind"] in KNOWN_HARD, rule
        assert rule.get("rationale"), "each rule must justify itself"


def test_causes_entails_forward_direction_only():
    """CAUSES(A,B) -> relation_direction source=A target=B, and not the inverse."""
    rules = {r["kind"]: r for r in _contract("causes.v1.json")["entailment"]}
    rd = rules["relation_direction"]
    assert rd["source"] == "$subject"
    assert rd["target"] == "$object"
    # the inverse assertion must not be present
    assert not (rd["source"] == "$object" and rd["target"] == "$subject")


def test_causes_entails_temporal_precedence():
    rules = {r["kind"]: r for r in _contract("causes.v1.json")["entailment"]}
    tp = rules["temporal_precedence"]
    assert tp["before"] == "$subject"
    assert tp["after"] == "$object"


def test_causes_entities_must_exist_and_end_on_effect():
    rules = {r["kind"]: r for r in _contract("causes.v1.json")["entailment"]}
    assert rules["final_focus"]["object"] == "$object"


def test_follows_is_purely_temporal():
    rules = {r["kind"]: r for r in _contract("follows.v1.json")["entailment"]}
    assert "relation_direction" not in rules, "FOLLOWS is ordering, not a graph edge"
    assert rules["temporal_precedence"]["before"] == "$subject"
    assert rules["final_focus"]["object"] == "$object"


def test_connects_is_directed():
    rules = {r["kind"]: r for r in _contract("connects.v1.json")["entailment"]}
    rd = rules["relation_direction"]
    assert rd["relation_type"] == "connects"
    assert rd["source"] == "$subject"
    assert rd["target"] == "$object"


def test_direction_is_not_symmetric_across_all_contracts():
    """No contract may claim both A->B and B->A for the same edge."""
    for name in CONTRACTS:
        for r in _contract(name)["entailment"]:
            if r["kind"] == "relation_direction":
                assert not (r["source"] == "$object" and r["target"] == "$subject"), name
