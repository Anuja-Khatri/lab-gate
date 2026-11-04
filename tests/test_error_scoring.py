"""Item-0 guard (D-030): an LLM ERROR (unparseable/empty/quota) must be scored as
REDUCED n, never as a verdict, and no completed registry metric may be ERROR-derived.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval import metrics
from eval.baselines import llm_gate as G

RESULTS = Path(__file__).resolve().parent.parent / "results"


def test_non_verdicts_excluded_from_n():
    # ERROR / DEFERRED / CACHE_MISS / UNPARSEABLE / "" are not verdicts
    decisions = ["PASS", "BLOCK", "ABSTAIN", "ERROR", "DEFERRED", "CACHE_MISS", "UNPARSEABLE", ""]
    dec = metrics.decided(decisions)
    assert dec == ["PASS", "BLOCK", "ABSTAIN"]
    # a false-block rate over these is 0/3 with n=3, NOT 0/8, and 5 excluded
    r = metrics.rate_over_decided(decisions, lambda d: d == "BLOCK")
    assert r["n"] == 3 and r["value"] == round(1 / 3, 6) and r["n_errors_excluded"] == 5


def test_error_never_counted_as_abstain():
    # a run that is all ERROR must yield n=0 (not an abstain/false-block rate of 0.0)
    r = metrics.rate_over_decided(["ERROR"] * 50, lambda d: d == "ABSTAIN")
    assert r["n"] == 0 and r["n_errors_excluded"] == 50


def test_llm_gate_unparseable_returns_error_not_abstain(monkeypatch):
    # the gate must map unparseable/empty model output to ERROR, never ABSTAIN (D-030)
    from gate.registry.lock import load_and_hash
    reg = load_and_hash()[0]
    plan = {"requester": {"id": "a", "cls": "internal_agent"}, "campaign_name": "c",
            "campaign_class": "activelearn",
            "actions": [{"server": "CPSIM", "action_name": "measure_cp",
                         "action_params": {"comp_vec": [0, 10, 0, 0, 10, 0, 0, 0, 20, 0, 0, 60, 0],
                                           "acquisition_rate": 0.2}}]}
    monkeypatch.setattr(G.llm, "call",
                        lambda *a, **k: {"text": "", "cache_source": "live"})  # truncated/empty
    assert G.llm_verdict(plan, reg, model="claude-opus-5-5")["verdict"] == "ERROR"
    monkeypatch.setattr(G.llm, "call",
                        lambda *a, **k: {"text": "here is my analysis, no json", "cache_source": "live"})
    assert G.llm_verdict(plan, reg, model="claude-opus-5-5")["verdict"] == "ERROR"


def test_no_completed_metric_is_blocked_or_errorish_numeric():
    """Blocked arms must be null (not a stand-in number); numeric metrics must be real
    rates in [0,1] (or a curve/dict/int), never a sentinel."""
    data = json.loads((RESULTS / "registry.json").read_text())
    for m in data["metrics"]:
        v = m["value"]
        if v is None:
            # blocked, not measured: must say so in a caveat
            assert any("blocked" in c.lower() for c in m.get("caveats", [])), m["metric_id"]
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            assert -1e-9 <= v <= 1.0 + 1e-9 or m["metric_id"].startswith(("latency", "llm.spend")), \
                f"{m['metric_id']}={v} out of rate range"
