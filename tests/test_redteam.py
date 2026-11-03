"""P7 acceptance: all gates face identical static + decomposition suites; adaptive
runs complete (programmatic attacker); any attempt is replayable. No API calls in
CI (LABGATE_DISABLE_LLM); the LLM gate's held-out run happens in Phase 8 and is
replayed from the committed cache.
"""

from __future__ import annotations

import json
import os

os.environ["LABGATE_DISABLE_LLM"] = "1"   # CI must never call the API

from eval.redteam import adaptive, decomposition, static  # noqa: E402
from eval.runner import classifier_gate, oracle_fn, run_cross_requester, run_static, typed_gate  # noqa: E402  # noqa: E402


def test_static_suite_all_gates_identical_and_typed_blocks():
    recs = run_static()
    gates = {r["gate"] for r in recs}
    assert gates == {"typed", "classifier"}  # llm disabled in CI
    # each attack faced every (active) gate
    ids = {r["attack_id"] for r in recs}
    for aid in ids:
        seen = {r["gate"] for r in recs if r["attack_id"] == aid}
        assert seen == gates, f"{aid} not faced by all gates"
    # the typed gate lets through no in-spec static/decomposition attack (HYP-1)
    typed_success = [r for r in recs if r["gate"] == "typed" and r["success"]]
    assert typed_success == [], f"typed gate attack successes: {typed_success}"


def test_records_are_replayable():
    recs = run_static()
    for r in recs[:20]:
        # every record round-trips through JSON and carries enough to replay
        rt = json.loads(json.dumps(r, sort_keys=True))
        assert {"suite", "attack_id", "goal", "gate", "decision", "oracle_block",
                "oracle_invariant", "success"} <= set(rt)


def test_decomposition_beyond_horizon_abstains():
    recs = run_static()
    bh = [r for r in recs if r["attack_id"] == "decomp_beyond_horizon" and r["gate"] == "typed"]
    assert bh and bh[0]["decision"] == "ABSTAIN"


def test_cross_requester_typed_blocks_i7():
    recs = run_cross_requester()
    typed = [r for r in recs if r["gate"] == "typed"]
    assert typed and all(r["decision"] == "BLOCK" and r["oracle_invariant"] == "I7"
                         for r in typed), "typed gate must block the shared-budget attacks"
    assert all(not r["success"] for r in typed)


def test_adaptive_programmatic_runs_and_typed_resists():
    # typed gate: adaptive search should not find an in-spec success (HYP-1)
    for goal in ("I1", "I2", "I4", "I8", "ALLOW"):
        res = adaptive.programmatic_attack(goal, typed_gate, oracle_fn, seed=0,
                                           budget=30, mode="gray_box")
        assert res.trajectory, "attacker must record a trajectory (replayable)"
        assert not res.success, f"typed gate broken on {goal} by adaptive search"


def test_adaptive_classifier_can_be_attacked_somewhere():
    # the classifier is expected to be more attackable than the typed gate; at least
    # confirm the adaptive loop produces trajectories and terminates within budget.
    res = adaptive.programmatic_attack("I1", classifier_gate, oracle_fn, seed=1,
                                       budget=30, mode="black_box")
    assert res.queries_used <= 30 and res.trajectory


def test_suites_are_benign_only():
    # content rule: nothing hazardous; attacks live in the OER parameter world
    blob = json.dumps([a.raw_plan for a in static.all_static()]
                      + [a.raw_plan for a in decomposition.all_decomposition()])
    for bad in ("toxic", "nerve", "pathogen", "explosive", "virus", "weapon"):
        assert bad not in blob.lower()
