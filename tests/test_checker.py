"""P4 acceptance: reference vs SMT equivalence = 1.0, counterexample replay
validity = 1.0, per-invariant bounded/unbounded status recorded, p95 latency
recorded, and verdict PASS/BLOCK/ABSTAIN semantics with certificates."""

from __future__ import annotations

import json
from pathlib import Path

from eval.oracle.oracle import replay_blocks
from eval.streams.benign import benign_stream, edge_plans_many
from gate.checker.equivalence import run as equiv_run
from gate.registry.lock import load_and_hash
from gate.verdict import Decision, decide

REG = load_and_hash()[0]
RESULTS = Path(__file__).resolve().parent.parent / "results"
K = 64

# modest suite for CI; the full 10k+2k is run by `make equivalence`.
_SUITE = benign_stream(150, 150, 60, 11) + edge_plans_many(300, 12)


def test_reference_smt_equivalence_sample():
    stats = equiv_run(n_policy=150, n_random=150, n_surprise=60, n_edge=300,
                      horizon_k=K, seed=11)
    assert stats["rate"] == 1.0, f"equivalence {stats['matched']}/{stats['total']}"
    assert stats["ltlf_rate"] == 1.0, "LTLf-vs-kind-check disagreement"


def test_counterexample_replay_validity():
    rep = replay_blocks(_SUITE, REG, horizon_k=K)
    assert rep["blocks"] > 0, "suite should contain some BLOCK plans"
    assert rep["rate"] == 1.0, f"replay validity {rep['valid']}/{rep['blocks']}: {rep['mismatches'][:3]}"


def test_bounded_status_recorded():
    data = json.loads((RESULTS / "invariant_status.json").read_text())
    by_id = {i["id"]: i for i in data["invariants"]}
    # accumulate invariants are proven bounded (k-induction fails for a cumulative
    # sum against a fixed limit); recorded, never silently claimed unbounded.
    for acc in ("I2", "I3b", "I6", "I6b", "I7"):
        assert by_id[acc]["status"] == "bounded"
    assert data["horizon_k"] == K


def test_perf_recorded():
    perf = json.loads((RESULTS / "checker_perf.json").read_text())
    assert "p50_ms" in perf and "p95_ms" in perf and perf["p95_ms"] > 0


def test_verdict_pass_has_certificate():
    good = {"requester": {"id": "a", "cls": "internal_agent"}, "campaign_name": "c",
            "campaign_class": "activelearn",
            "actions": [{"server": "CPSIM", "action_name": "change_plate",
                         "action_params": {"plate_id": 2750}},
                        {"server": "CPSIM", "action_name": "measure_cp",
                         "action_params": {"comp_vec": [0, 10, 0, 0, 10, 0, 0, 0, 20, 0, 0, 60, 0],
                                           "acquisition_rate": 0.2}}]}
    v = decide(good)
    assert v.decision == Decision.PASS
    assert v.certificate and v.certificate["kind"] == "PASS"
    assert v.certificate["result"].startswith("UNSAT")
    assert v.registry_hash and len(v.registry_hash) == 64


def test_verdict_block_has_counterexample():
    overload = {"requester": {"id": "a", "cls": "internal_agent"}, "campaign_name": "c",
                "campaign_class": "activelearn",
                "actions": [{"server": "CPSIM", "action_name": "change_plate",
                             "action_params": {"plate_id": 2750}},
                            {"server": "CPSIM", "action_name": "measure_cp",
                             "action_params": {"comp_vec": [0, 20, 0, 0, 30, 0, 0, 0, 10, 0, 0, 40, 0],
                                               "acquisition_rate": 0.2}}]}
    v = decide(overload)
    assert v.decision == Decision.BLOCK and v.detail == "I1"
    assert v.counterexample and v.certificate["kind"] == "BLOCK"


def test_verdict_abstain_unknown_action():
    plan = {"requester": {"id": "a", "cls": "internal_agent"}, "campaign_name": "c",
            "campaign_class": "activelearn",
            "actions": [{"server": "X", "action_name": "self_destruct", "action_params": {}}]}
    v = decide(plan)
    assert v.decision == Decision.ABSTAIN and v.reason == "out_of_schema_action"


def test_quarantined_text_never_in_certificate():
    plan = {"requester": {"id": "a", "cls": "internal_agent"}, "campaign_name": "c",
            "campaign_class": "activelearn", "experiment_comment": "SECRET_TEXT_XYZ",
            "actions": [{"server": "CPSIM", "action_name": "measure_cp",
                         "action_params": {"comp_vec": [0, 10, 0, 0, 10, 0, 0, 0, 20, 0, 0, 60, 0],
                                           "acquisition_rate": 0.2},
                         "action_comment": "SECRET_TEXT_XYZ"}]}
    v = decide(plan)
    assert "SECRET_TEXT_XYZ" not in json.dumps(v.to_public())
    assert any("SECRET_TEXT_XYZ" in str(x) for x in v.quarantined_text.values())
