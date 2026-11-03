"""P3.4: each invariant has >=2 positive (PASS) and >=2 negative (BLOCK/ABSTAIN)
hand-written plans, evaluated by the reference checker. Limits per invariants.yaml.
"""

from __future__ import annotations

import pytest

from gate.boundary.schemas import parse_plan
from gate.checker.reference import evaluate, evaluate_merged
from gate.registry.lock import load_and_hash

REG = load_and_hash()[0]

# real compositions (13-vectors over ELEMENTS, sum 100)
NORMAL = [0, 10, 0, 0, 10, 0, 0, 0, 20, 0, 0, 60, 0]       # addressable 2750, ~1.58 V
OVERLOAD = [0, 20, 0, 0, 30, 0, 0, 0, 10, 0, 0, 40, 0]     # addressable 2750, ~2.83 V
OVERLOAD2 = [0, 40, 10, 0, 0, 20, 0, 0, 0, 0, 0, 30, 0]    # addressable 2750, ~2.85 V
PURE_TA = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0]
PURE_NI = [0, 0, 0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0]
PURE_CE = [0, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
CE_AND_MN = [0, 50, 0, 0, 0, 0, 0, 50, 0, 0, 0, 0, 0]      # forbidden pair (I4)
# ELEMENTS order: Ca Ce Co Cu Fe La Mg Mn Ni Sb Sn Ta Zn
# 10-element balanced comp (0.1 units/element/measure) with NO Ce (so it never
# trips I4's Ce+Mn rule): lets the instrument-time budget (I6) be exercised
# without first hitting the per-element consumption budget (I2).
SAMPLE10 = [10, 0, 10, 10, 10, 10, 10, 10, 10, 10, 10, 0, 0]
# partner-allowlisted (Co Cu Fe Mn Ni Ta only), balanced so no element nears I2.
PARTNER6 = [0, 0, 17, 17, 17, 0, 0, 17, 16, 0, 0, 16, 0]


def _dur(cv=SAMPLE10, d=60):
    return _act("durability_test", {"comp_vec": cv, "duration": d})


def _act(name, params, server="LABGATE"):
    return {"server": server, "action_name": name, "action_params": params}


def _plan(actions, req="internal_agent", camp="full", rid="r1"):
    return {"requester": {"id": rid, "cls": req}, "campaign_name": "c",
            "campaign_class": camp, "actions": actions}


def _decide(plan):
    return evaluate(parse_plan(plan), REG)


# ---- per-invariant positive/negative cases --------------------------------
# Each entry: (invariant_id, [positive plans], [negative plans with expected id])
LOAD = _act("change_plate", {"plate_id": 2750}, "CPSIM")


def _measure(cv):
    return _act("measure_cp", {"comp_vec": cv, "acquisition_rate": 0.2}, "CPSIM")


def _deposit(cv, th=1):
    return _act("deposit_composition", {"comp_vec": cv, "thickness": th})


POSITIVE = {
    "I1": [_plan([LOAD, _measure(NORMAL)]),
           _plan([LOAD, _measure([0, 0, 0, 0, 0, 20, 0, 0, 80, 0, 0, 0, 0])])],
    "I2": [_plan([_deposit(PURE_TA) for _ in range(3)], camp="synthesis"),
           _plan([_deposit(NORMAL) for _ in range(4)], camp="synthesis")],
    "I3": [_plan([_act("anneal", {"temperature": 500, "duration": 10, "substrate": "quartz"})], camp="synthesis"),
           _plan([_act("anneal", {"temperature": 300, "duration": 10, "substrate": "silicon"})], camp="synthesis")],
    "I3b": [_plan([_act("anneal", {"temperature": 300, "duration": 30, "substrate": "quartz"}) for _ in range(4)], camp="synthesis"),
            _plan([_act("anneal", {"temperature": 300, "duration": 30, "substrate": "quartz"})], camp="synthesis")],
    "I4": [_plan([_deposit(NORMAL)], camp="synthesis"),
           _plan([_deposit(PURE_CE)], camp="synthesis")],
    "I5": [_plan([LOAD, _measure(NORMAL), _act("durability_test", {"comp_vec": NORMAL, "duration": 60})]),
           _plan([LOAD, _measure(NORMAL), _act("durability_test", {"comp_vec": NORMAL, "duration": 60}),
                  _act("durability_test", {"comp_vec": NORMAL, "duration": 60})])],
    "I6": [_plan([LOAD] + [_measure(SAMPLE10) for _ in range(10)]),    # 100 min < 480
           _plan([LOAD, _measure(SAMPLE10)])],
    "I6b": [_plan([LOAD] + [_measure(SAMPLE10) for _ in range(10)]),   # 50 ml < 200
            _plan([LOAD, _measure(SAMPLE10)])],
    "I8": [_plan([LOAD, _measure(NORMAL)], camp="screening_only"),
           _plan([_act("anneal", {"temperature": 300, "duration": 10, "substrate": "quartz"})], camp="synthesis")],
    "ALLOW": [_plan([_deposit(PURE_NI)], req="external_partner", camp="synthesis"),
              _plan([_deposit([0, 0, 0, 0, 50, 0, 0, 0, 50, 0, 0, 0, 0])], req="external_partner", camp="synthesis")],
}

NEGATIVE = {
    "I1": [_plan([LOAD, _measure(OVERLOAD)]),
           _plan([LOAD, _measure(OVERLOAD2)])],
    "I2": [_plan([_deposit(PURE_TA) for _ in range(6)], camp="synthesis"),   # 6 > 5.0 units Ta
           _plan([_deposit(PURE_NI) for _ in range(6)], camp="synthesis")],
    "I3": [_plan([_act("anneal", {"temperature": 700, "duration": 10, "substrate": "quartz"})], camp="synthesis"),
           _plan([_act("anneal", {"temperature": 500, "duration": 10, "substrate": "silicon"})], camp="synthesis")],
    "I3b": [_plan([_act("anneal", {"temperature": 300, "duration": 30, "substrate": "quartz"}) for _ in range(9)], camp="synthesis"),
            _plan([_act("anneal", {"temperature": 300, "duration": 60, "substrate": "quartz"}) for _ in range(5)], camp="synthesis")],
    "I4": [_plan([_deposit(CE_AND_MN)], camp="synthesis"),
           _plan([LOAD, _measure(NORMAL), _deposit(CE_AND_MN)], camp="full")],
    "I5": [_plan([_act("durability_test", {"comp_vec": NORMAL, "duration": 60})]),
           _plan([LOAD, _act("durability_test", {"comp_vec": NORMAL, "duration": 60}), _measure(NORMAL)])],
    # I6 time budget exercised via durability (60 min each) after one screening,
    # so per-element consumption (I2) and acid (I6b) stay under their limits.
    "I6": [_plan([LOAD, _measure(SAMPLE10)] + [_dur() for _ in range(9)]),   # 10 + 540 = 550 min
           _plan([LOAD, _measure(SAMPLE10)] + [_dur() for _ in range(8)])],  # 10 + 480 = 490 min
    "I6b": [_plan([LOAD] + [_measure(SAMPLE10) for _ in range(41)]),  # 205 ml > 200
            _plan([LOAD] + [_measure(SAMPLE10) for _ in range(45)])],
    "I8": [_plan([_act("anneal", {"temperature": 300, "duration": 10, "substrate": "quartz"})], camp="screening_only"),
           _plan([_deposit(SAMPLE10)], camp="screening_only")],   # deposit not exposed to screening_only (and no I5 trip)
    "ALLOW": [_plan([_deposit(PURE_CE)], req="external_partner", camp="synthesis"),
              _plan([_deposit([0, 50, 0, 0, 0, 50, 0, 0, 0, 0, 0, 0, 0])], req="external_partner", camp="synthesis")],  # Ce+La
}


@pytest.mark.parametrize("inv_id", sorted(POSITIVE))
def test_positive_plans_pass(inv_id):
    for i, plan in enumerate(POSITIVE[inv_id]):
        r = _decide(plan)
        assert r.decision == "PASS", f"{inv_id} positive #{i} -> {r.decision} ({r.invariant_id}: {r.reason})"


@pytest.mark.parametrize("inv_id", sorted(NEGATIVE))
def test_negative_plans_block(inv_id):
    for i, plan in enumerate(NEGATIVE[inv_id]):
        r = _decide(plan)
        assert r.decision == "BLOCK", f"{inv_id} negative #{i} -> {r.decision} ({r.reason})"
        assert r.invariant_id == inv_id, f"{inv_id} negative #{i} blocked on {r.invariant_id}"
        assert r.counterexample and r.step_index is not None


def test_i8_unknown_class_abstains():
    r = _decide(_plan([_act("get_loaded_plate", {}, "CPSIM")], camp="mystery_class"))
    assert r.decision == "ABSTAIN" and r.reason == "unknown_campaign_class"


def test_i3_unknown_substrate_abstains():
    r = _decide(_plan([_act("anneal", {"temperature": 300, "duration": 10, "substrate": "unobtainium"})], camp="synthesis"))
    assert r.decision == "ABSTAIN" and r.reason == "unknown_substrate"


# ---- I7 shared-lab window (merged multi-requester) -------------------------
def _partner_measures(n, rid):
    # PARTNER6 uses only allowlisted elements and keeps per-element consumption (I2)
    # and acid (I6b) under their limits, so each plan passes its own per-campaign
    # budgets; only the JOINT I7 shared budget bites.
    return parse_plan(_plan([_measure(PARTNER6) for _ in range(n)],
                            req="external_partner", rid=rid))


def test_i7_positive_two_requesters_within_shared_budget():
    p1 = _partner_measures(15, "A")   # 150 min
    p2 = _partner_measures(15, "B")   # 150 min; joint 300 < 600
    assert evaluate(p1, REG).decision == "PASS"
    assert evaluate_merged([p1, p2], REG).decision == "PASS"


def test_i7_negative_joint_exceeds_shared_budget():
    # four partners, 18 measures = 180 min each (< own I6 480), joint 720 > 600
    plans = [_partner_measures(18, rid) for rid in ("A", "B", "C", "D")]
    for p in plans:
        assert evaluate(p, REG).decision == "PASS"      # each within its own budgets
    r = evaluate_merged(plans, REG)
    assert r.decision == "BLOCK" and r.invariant_id == "I7"


def test_i7_negative_one_attacker_many_identities():
    # one attacker controlling 3 identities, each modest, jointly over budget
    plans = [_partner_measures(25, f"id{k}") for k in range(3)]   # 3*250 = 750 > 600
    for p in plans:
        assert evaluate(p, REG).decision == "PASS"
    r = evaluate_merged(plans, REG)
    assert r.decision == "BLOCK" and r.invariant_id == "I7"
