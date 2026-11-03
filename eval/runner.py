"""Red-team / evaluation runner (P7.5, drives Phases 7-8).

Faces each gate with the static, decomposition, cross-requester, and adaptive
suites; consults the oracle for ground-truth harm; and writes a replayable JSONL
log (seed, mode, plan hash, gate verdict, oracle result). Attack success = gate
PASSES and the oracle observes the target invariant violated.

Gates:
  * typed  - gate.verdict.decide (the gate under test)
  * classifier - eval.baselines.classifier.predict (BLOCK if harmful else PASS)
  * llm    - eval.baselines.llm_gate (DEFERRED under D-020; recorded, not fabricated)

All three face the identical static + decomposition suites (P7 acceptance); the LLM
gate is recorded as deferred where keys are absent (R-08 partial, reported).
"""

from __future__ import annotations

import json
from pathlib import Path

from eval import llm
from eval.baselines import llm_gate as llm_gate_mod
from eval.baselines.classifier import predict as clf_predict
from eval.oracle.oracle import observe
from eval.redteam import adaptive, decomposition, static
from gate.boundary.schemas import parse_plan
from gate.registry.lock import load_and_hash
from gate.verdict import decide, decide_merged, plan_hash

REPO = Path(__file__).resolve().parent.parent
LOG = REPO.parent / "logs" / "redteam_log.jsonl"
_REG = load_and_hash()[0]


# --- gate functions: raw_plan -> (decision, info) ---------------------------
def typed_gate(raw_plan):
    v = decide(raw_plan)
    return v.decision.value, {"blocked_invariant": v.detail or "", "plan_hash": v.plan_hash}


def classifier_gate(raw_plan, model="gb"):
    out = clf_predict(raw_plan, model)
    return ("BLOCK" if out["harmful"] else "PASS"), {"score": out["score"]}


def llm_gate_fn(raw_plan):
    v = llm_gate_mod.llm_verdict(raw_plan, _REG)   # raises LLMKeysMissing if no key
    return v["verdict"], {"rule": v.get("rule")}


def oracle_fn(raw_plan):
    r = observe(parse_plan(raw_plan), _REG)
    return (r.decision == "BLOCK", r.invariant_id or "")


GATES = {"typed": typed_gate, "classifier": classifier_gate}
# llm gate added only if a key is present; else recorded as deferred.


def _llm_available() -> bool:
    try:
        # a cheap probe: build a request and see if a key exists (no call)
        return llm._key_for("openai") is not None
    except Exception:
        return False


# --- suites -----------------------------------------------------------------
def run_static(log_fh=None) -> list[dict]:
    recs = []
    attacks = static.all_static() + decomposition.all_decomposition()
    for atk in attacks:
        o_block, o_inv = oracle_fn(atk.raw_plan)
        ph = plan_hash(parse_plan(atk.raw_plan))
        for gate_name, gate_fn in _active_gates().items():
            decision, info = _safe_gate(gate_fn, atk.raw_plan)
            success = (decision == "PASS" and o_block and
                       (o_inv == atk.goal or atk.goal == "injection"))
            rec = {"suite": atk.category, "attack_id": atk.attack_id, "goal": atk.goal,
                   "gate": gate_name, "decision": decision, "oracle_block": o_block,
                   "oracle_invariant": o_inv, "success": success, "plan_hash": ph,
                   "note": atk.note}
            recs.append(rec)
            if log_fh:
                log_fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return recs


def run_cross_requester(log_fh=None) -> list[dict]:
    recs = []
    for atk in decomposition.cross_requester():
        parsed = [parse_plan(p) for p in atk.raw_plans]
        # oracle: merged schedule harm
        from gate.checker.reference import evaluate_merged
        omerged = evaluate_merged(parsed, _REG)
        o_block = omerged.decision == "BLOCK"
        o_inv = omerged.invariant_id or ""
        # typed gate: merged decision
        tv = decide_merged(atk.raw_plans)
        t_success = (tv.decision.value == "PASS" and o_block and o_inv == atk.goal)
        recs.append({"suite": atk.category, "attack_id": atk.attack_id, "goal": atk.goal,
                     "gate": "typed", "decision": tv.decision.value, "oracle_block": o_block,
                     "oracle_invariant": o_inv, "success": t_success,
                     "requester_count": atk.requester_count, "note": atk.note})
        # classifier: per-plan; PASS only if NO individual plan is flagged
        any_flag = any(clf_predict(p)["harmful"] for p in atk.raw_plans)
        c_decision = "BLOCK" if any_flag else "PASS"
        c_success = (c_decision == "PASS" and o_block and o_inv == atk.goal)
        recs.append({"suite": atk.category, "attack_id": atk.attack_id, "goal": atk.goal,
                     "gate": "classifier", "decision": c_decision, "oracle_block": o_block,
                     "oracle_invariant": o_inv, "success": c_success,
                     "requester_count": atk.requester_count, "note": atk.note})
        n_new = 2
        # LLM gate (held-out only): per-plan; PASS unless it flags some plan.
        if "llm" in _active_gates():
            try:
                any_llm_block = any(llm_gate_fn(p)[0] == "BLOCK" for p in atk.raw_plans)
                l_decision = "BLOCK" if any_llm_block else "PASS"
            except llm.LLMKeysMissing:
                l_decision = "DEFERRED"
            l_success = (l_decision == "PASS" and o_block and o_inv == atk.goal)
            recs.append({"suite": atk.category, "attack_id": atk.attack_id, "goal": atk.goal,
                         "gate": "llm", "decision": l_decision, "oracle_block": o_block,
                         "oracle_invariant": o_inv, "success": l_success,
                         "requester_count": atk.requester_count, "note": atk.note})
            n_new = 3
        if log_fh:
            for r in recs[-n_new:]:
                log_fh.write(json.dumps(r, sort_keys=True) + "\n")
    return recs


def run_adaptive(goals=None, seeds=None, budget=200, modes=("black_box", "gray_box"),
                 log_fh=None) -> list[dict]:
    import yaml
    goals = goals or [g["id"] for g in yaml.safe_load(
        (REPO / "eval" / "redteam" / "goals.yaml").read_text())["goals"]]
    seeds = seeds if seeds is not None else list(range(10))
    recs = []
    for gate_name, gate_fn in _active_gates().items():
        named = _named(gate_fn, gate_name)
        for goal in goals:
            for mode in modes:
                for seed in seeds:
                    res = adaptive.programmatic_attack(goal, named, oracle_fn, seed,
                                                       budget=budget, mode=mode)
                    rec = {"suite": "adaptive", "goal": goal, "gate": gate_name,
                           "mode": mode, "seed": seed, "success": res.success,
                           "queries_used": res.queries_used, "budget": budget,
                           "attacker": "programmatic"}
                    recs.append(rec)
                    if log_fh:
                        log_fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return recs


def _active_gates() -> dict:
    gates = dict(GATES)
    # LABGATE_DISABLE_LLM guards CI/tests so they never call the API; the LLM gate
    # is included only for the real held-out eval (make eval) when a key is present.
    import os
    if os.environ.get("LABGATE_DISABLE_LLM") != "1" and _llm_available():
        gates["llm"] = llm_gate_fn
    return gates


def _named(fn, name):
    fn.__name__ = name
    return fn


def _safe_gate(gate_fn, raw_plan):
    try:
        return gate_fn(raw_plan)
    except llm.LLMKeysMissing:
        return "DEFERRED", {}


def main(adaptive_seeds=2, adaptive_budget=50) -> dict:
    """Run a representative evaluation and write the replayable log. Full-scale
    held-out parameters are set in config/experiment.yaml and used by Phase 8."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "w") as fh:
        static_recs = run_static(fh)
        xreq_recs = run_cross_requester(fh)
        adapt_recs = run_adaptive(seeds=list(range(adaptive_seeds)),
                                  budget=adaptive_budget, log_fh=fh)
    llm_status = "available" if _llm_available() else "DEFERRED (no key; D-020)"
    summary = {"n_static": len(static_recs), "n_cross_requester": len(xreq_recs),
               "n_adaptive": len(adapt_recs), "llm_gate": llm_status,
               "log": str(LOG)}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    main()
