"""P5 acceptance: gate runs inside the OERSIM loop with zero changes to
helao-async; gate-disabled byte-identity with stock OERSIM; every verdict produces
a receipt."""

from __future__ import annotations

import json

from gate.hook.dispatch_hook import gate_dispatch, gate_dispatch_merged
from gate.hook.oersim_hook import run_gated
from gate.receipts import make_receipt
from gate.verdict import decide
from sim_ext.oersim import canonical_json, run_activelearn

SEED = 20261103
NORMAL = [0, 10, 0, 0, 10, 0, 0, 0, 20, 0, 0, 60, 0]
OVERLOAD = [0, 20, 0, 0, 30, 0, 0, 0, 10, 0, 0, 40, 0]


def _act(name, params, server="CPSIM"):
    return {"server": server, "action_name": name, "action_params": params}


def _plan(actions, req="internal_agent", camp="activelearn", rid="r"):
    return {"requester": {"id": rid, "cls": req}, "campaign_name": "c",
            "campaign_class": camp, "actions": actions}


def test_gate_disabled_byte_identical_to_stock(tmp_path):
    stock = canonical_json(run_activelearn(2750, 8, SEED))
    gated_off = canonical_json(run_gated(2750, 8, SEED, gate_enabled=False))
    assert stock == gated_off, "gate-disabled run must be byte-identical to stock OERSIM"


def test_gated_loop_runs_and_passes_benign(tmp_path):
    res = run_gated(2750, 5, SEED, gate_enabled=True,
                    receipts_path=tmp_path / "r.jsonl",
                    abstain_queue_path=tmp_path / "q.jsonl")
    assert res["status"] in ("completed", "held_for_human")
    assert res["verdicts"], "there should be decision receipts"
    # benign active-learning should commit at least some measurements
    assert res["n_committed"] >= 1


def test_block_cancels_and_abstain_holds(tmp_path):
    # unknown campaign class forces ABSTAIN at the decision step -> hold
    res = run_gated(2750, 5, SEED, gate_enabled=True, campaign_class="mystery",
                    receipts_path=tmp_path / "r.jsonl",
                    abstain_queue_path=tmp_path / "q.jsonl")
    assert res["status"] == "held_for_human"
    assert (tmp_path / "q.jsonl").exists()
    q = (tmp_path / "q.jsonl").read_text().strip().splitlines()
    assert len(q) >= 1 and json.loads(q[0])["reason"] == "unknown_campaign_class"


def test_every_verdict_writes_a_receipt(tmp_path):
    rpath = tmp_path / "r.jsonl"
    run_gated(2750, 4, SEED, gate_enabled=True, receipts_path=rpath,
              abstain_queue_path=tmp_path / "q.jsonl")
    lines = rpath.read_text().strip().splitlines()
    assert lines, "receipts must be written"
    rec = json.loads(lines[0])
    for key in ("timestamp", "gate_version", "plan_hash", "registry_hash",
                "decision", "certificate", "quarantined_text"):
        assert key in rec


def test_receipt_stores_but_checker_never_reads_text():
    plan = _plan([_act("measure_cp", {"comp_vec": NORMAL, "acquisition_rate": 0.2})],
                 ) | {"experiment_comment": "AUDIT_ONLY_TEXT"}
    plan["actions"][0]["action_comment"] = "AUDIT_ONLY_TEXT"
    v = decide(plan)
    rec = make_receipt(v, timestamp="2026-11-03T00:00:00+00:00")
    # text is in the receipt's quarantined store...
    assert any("AUDIT_ONLY_TEXT" in str(x) for x in rec["quarantined_text"].values())
    # ...but never in the certificate / counterexample (checker I/O)
    assert "AUDIT_ONLY_TEXT" not in json.dumps(rec["certificate"])
    assert "AUDIT_ONLY_TEXT" not in json.dumps(rec["counterexample"])


def test_dispatch_hook_routing(tmp_path):
    rp = tmp_path / "r.jsonl"
    routing, v = gate_dispatch(_plan([_act("change_plate", {"plate_id": 2750}),
                                      _act("measure_cp", {"comp_vec": NORMAL, "acquisition_rate": 0.2})]),
                               receipts_path=rp)
    assert routing == "proceed"
    routing, v = gate_dispatch(_plan([_act("change_plate", {"plate_id": 2750}),
                                      _act("measure_cp", {"comp_vec": OVERLOAD, "acquisition_rate": 0.2})]),
                               receipts_path=rp)
    assert routing == "cancel" and v.detail == "I1"
    routing, v = gate_dispatch(_plan([_act("self_destruct", {}, "X")]), receipts_path=rp)
    assert routing == "hold"


def test_dispatch_merged_i7(tmp_path):
    def partner(n, rid):
        acts = [_act("measure_cp", {"comp_vec": [0, 0, 17, 17, 17, 0, 0, 17, 16, 0, 0, 16, 0],
                                    "acquisition_rate": 0.2}) for _ in range(n)]
        return _plan(acts, req="external_partner", rid=rid)
    routing, v = gate_dispatch_merged([partner(25, "a"), partner(25, "b"), partner(25, "c")],
                                      receipts_path=tmp_path / "r.jsonl")
    assert routing == "cancel" and v.detail == "I7"
