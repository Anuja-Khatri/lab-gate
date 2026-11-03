"""P3 acceptance (a): registry validates against schema; hash stable across runs;
every invariant renders an LTLf formula + Dwyer pattern."""

from __future__ import annotations

from gate.registry.lock import DEFAULT_REGISTRY, load_and_hash, registry_hash
from gate.registry.schema import InvariantKind, load_registry

EXPECTED_IDS = {"I1", "I2", "I3", "I3b", "I4", "I5", "I6", "I6b", "I7", "I8", "ALLOW"}


def test_registry_validates_and_has_all_invariants():
    reg = load_registry(DEFAULT_REGISTRY)
    ids = {inv.id for inv in reg.invariants}
    assert ids == EXPECTED_IDS, f"unexpected ids: {ids ^ EXPECTED_IDS}"
    # every prose field and LTLf is present
    for inv in reg.invariants:
        assert inv.plain_english.strip()
        assert inv.rationale.strip()
        assert inv.source.strip()
        assert inv.ltlf and inv.pattern
        assert isinstance(inv.kind, (InvariantKind, str))
        inv.typed_spec()  # re-validates the kind-specific spec


def test_hash_stable_across_runs():
    reg1, h1 = load_and_hash()
    reg2, h2 = load_and_hash()
    assert h1 == h2 and len(h1) == 64
    # recomputing from a fresh load is identical
    assert registry_hash(load_registry(DEFAULT_REGISTRY)) == h1


def test_patterns_match_kinds():
    reg = load_registry(DEFAULT_REGISTRY)
    by_id = {inv.id: inv for inv in reg.invariants}
    assert by_id["I1"].pattern == "Universality"      # bound
    assert by_id["I4"].pattern == "Absence"           # forbid_combo
    assert by_id["I2"].pattern == "Universality"      # accumulate
    assert by_id["I3"].pattern == "Absence"           # reach banned
    assert by_id["I5"].pattern == "Precedence"        # reach ordering


def test_campaign_classes_and_allowlist_present():
    reg = load_registry(DEFAULT_REGISTRY)
    assert "screening_only" in reg.campaign_classes
    assert "anneal" not in reg.campaign_classes["screening_only"]
    assert "durability_test" not in reg.campaign_classes["screening_only"]
    assert set(reg.partner_element_allowlist) == {"Fe", "Mn", "Ni", "Ta", "Cu", "Co"}
