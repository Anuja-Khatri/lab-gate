"""Ground-truth oracle (P6.3) and counterexample replay (P4.6).

The oracle executes a plan in the simulator with accounting and evaluates the
registry invariants over the ACTUAL simulated state trace: it uses the REAL
measured potential for I1 (via sim_ext.surrogate.actual_erhe_v, which replays the
stored CP trace) rather than the gate's abstract surrogate. Harm = any invariant
violated in the actual trace. Because the gate's abstract model and the simulator's
real dynamics can differ, the gap between gate and oracle is a measurable failure
surface for the typed gate (HYP-2).

The oracle shares the invariant semantics with the reference checker (it calls
``evaluate`` with the actual potential provider), so a BLOCK's counterexample can be
replayed and confirmed invariant-for-invariant.
"""

from __future__ import annotations

from gate.boundary.schemas import ParsedPlan, parse_plan
from gate.checker.reference import RefResult, evaluate
from gate.registry.schema import Registry
from sim_ext.surrogate import actual_erhe_v


def observe(parsed: ParsedPlan, registry: Registry) -> RefResult:
    """Evaluate a plan over the ACTUAL simulated trace (ground truth, no horizon)."""
    return evaluate(parsed, registry, erhe_provider=actual_erhe_v, horizon_k=None)


def observe_raw(raw_plan: dict, registry: Registry) -> RefResult:
    return observe(parse_plan(raw_plan), registry)


def replay_blocks(suite: list[dict], registry: Registry, horizon_k: int) -> dict:
    """Counterexample replay (P4.6): for every plan the gate BLOCKs, execute it in
    the simulator (actual trace) and confirm the oracle observes the same invariant
    violated. The gate verdict uses the reference evaluator, which is proven
    equivalent to the SMT encoder (P4.5 = 1.0). Returns the replay-validity rate."""
    blocks = 0
    valid = 0
    mismatches = []
    for idx, rp in enumerate(suite):
        pp = parse_plan(rp)
        gate = evaluate(pp, registry, horizon_k=horizon_k)
        if gate.decision != "BLOCK":
            continue
        blocks += 1
        obs = observe(pp, registry)
        if obs.decision == "BLOCK" and obs.invariant_id == gate.invariant_id:
            valid += 1
        else:
            mismatches.append({"plan": idx, "gate_block": gate.invariant_id,
                               "oracle": f"{obs.decision}/{obs.invariant_id}"})
    rate = valid / blocks if blocks else 1.0
    return {"blocks": blocks, "valid": valid, "rate": rate, "mismatches": mismatches}
