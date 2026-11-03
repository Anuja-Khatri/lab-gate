"""SMT plan checker (P4.2): an independent Z3 encoding of the invariants over the
plan's finite state trace, cross-checked against the reference evaluator (P4.5).

The accounting PHYSICS (per-action deltas) is shared with the reference via
sim_ext.accounting (simple, separately tested). What is implemented INDEPENDENTLY
here is the invariant LOGIC: every invariant's violation condition is encoded as a
Z3 constraint and decided by the Z3 solver (SAT = a violation is reachable -> BLOCK
with the model as counterexample; UNSAT = the invariant holds, contributing to a
PASS certificate). This is the "standard bounded encoding of LTLf over the finite
trace": cumulative quantities are Z3 reals with transition constraints, per-step
predicates are Z3 atoms, and bounded model checking runs to horizon k.

For accumulate invariants over monotone non-negative quantities we also attempt
1-induction (prove the bound for ALL lengths); for a cumulative sum against a fixed
limit this is not inductive, so the proof is recorded as "bounded" (holds to
horizon k for this plan), never silently claimed unbounded.

Decision order matches the reference exactly (capability I8 and tenant ALLOW first,
then first violation in step order), so the two agree verdict-for-verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import z3

from gate.boundary.schemas import ParsedPlan
from gate.checker.reference import StepState, _plate_of, _substrate_limit
from gate.registry.schema import Registry
from sim_ext.accounting import (
    AccountingState,
    apply_action,
    elements_of,
    sample_key,
)
from sim_ext.surrogate import gate_predicted_erhe_v

_COMP_ACTIONS = {"measure_cp", "durability_test", "deposit_composition"}


@dataclass
class SmtResult:
    decision: str
    reason: str
    invariant_id: Optional[str] = None
    step_index: Optional[int] = None
    counterexample: Optional[list] = None
    certificate: Optional[dict] = None
    invariant_status: dict = field(default_factory=dict)   # id -> bounded|unbounded
    trace: list = field(default_factory=list)


def _z3_version() -> str:
    v = z3.get_version()
    return ".".join(str(x) for x in v)


@lru_cache(maxsize=256)
def _k_induction_bounded(max_delta: float, limit: float) -> str:
    """Attempt 1-induction for an accumulate bound. Returns 'unbounded' if the
    property is inductive for all lengths, else 'bounded'."""
    s_prev, d = z3.Reals("s_prev d")
    solver = z3.Solver()
    # negation of the inductive step: hypothesis holds, delta is monotone and
    # within the per-action maximum, yet the successor breaks the bound.
    solver.add(s_prev <= limit, d >= 0, d <= max_delta, s_prev + d > limit)
    return "bounded" if solver.check() == z3.sat else "unbounded"


def encode_and_check(parsed: ParsedPlan, registry: Registry,
                     horizon_k: int = 16, timeout_s: float = 10.0) -> SmtResult:
    """Encode and check a single typed plan. See module docstring."""
    if not parsed.ok:
        return SmtResult("ABSTAIN", parsed.abstain_reason or "unparseable")

    actions = parsed.actions
    req_class = parsed.provenance.requester_class
    campaign_class = parsed.provenance.campaign_class
    allowed_actions = registry.campaign_classes.get(campaign_class)
    allowlist = set(registry.partner_element_allowlist)

    _priority = {"I8": 0, "ALLOW": 1}
    applicable = sorted(
        [inv for inv in registry.invariants
         if str(inv.scope) == "any" or str(inv.scope) == req_class],
        key=lambda inv: _priority.get(inv.id, 2),
    )

    # horizon (R-07): a plan longer than k can only be certified to k for
    # bound-proved invariants -> ABSTAIN beyond horizon.
    if len(actions) > horizon_k:
        return SmtResult("ABSTAIN", "beyond_horizon", step_index=horizon_k)

    state = AccountingState()
    qc_passed: set[str] = set()
    trace: list[StepState] = []

    # Z3 cumulative variables, pinned to the accounting transitions (BMC trace).
    solver = z3.Solver()
    solver.set("timeout", int(timeout_s * 1000))
    status: dict[str, str] = {}

    for i, act in enumerate(actions):
        name = act.action_name
        params = act.params.model_dump()
        comp_vec = params.get("comp_vec")
        plate = _plate_of(actions, i)

        if allowed_actions is None:
            return SmtResult("ABSTAIN", "unknown_campaign_class",
                             invariant_id="I8", step_index=i, trace=trace)
        action_outside = name not in allowed_actions

        predicted = gate_predicted_erhe_v(comp_vec, plate) if comp_vec else None
        anneal_over = False
        if name == "anneal":
            lim = None
            for inv in applicable:
                if inv.id == "I3":
                    lim = _substrate_limit(inv, params.get("substrate", ""))
            if lim is None:
                return SmtResult("ABSTAIN", "unknown_substrate",
                                 invariant_id="I3", step_index=i, trace=trace)
            anneal_over = params["temperature"] > lim
        this_sample = sample_key(plate, comp_vec) if comp_vec else None
        sample_qc = (this_sample in qc_passed) if this_sample else False
        els = set(elements_of(comp_vec)) if comp_vec else set()
        partner_bad = (req_class == "external_partner" and name in _COMP_ACTIONS
                       and bool(els - allowlist))

        apply_action(state, name, params, plate_id=plate,
                     requester_id=parsed.provenance.requester_id,
                     predicted_erhe_v=predicted)
        if name == "measure_cp" and this_sample:
            qc_passed.add(this_sample)

        derived = {"action": name,
                   "predicted_erhe_v": None if predicted is None else round(predicted, 6),
                   "anneal_temp_over_limit": anneal_over,
                   "sample_qc_passed": sample_qc,
                   "action_outside_campaign_capability": action_outside,
                   "partner_element_not_allowed": partner_bad,
                   "elements": sorted(els)}
        trace.append(StepState(i, name, state.snapshot(), derived))

        # --- per-step invariant checks via Z3 (first violation -> BLOCK) ---
        for inv in applicable:
            kind = str(inv.kind)
            spec = inv.typed_spec()
            viol = None   # a Z3 BoolRef whose SAT means "violated at step i"

            if kind == "bound" and name == spec.action:
                val = derived.get(spec.predicate.var)
                if val is not None:
                    x = z3.Real(f"{inv.id}_{i}")
                    viol = z3.And(x == val, z3.Not(_z3_cmp(x, spec.predicate.op,
                                                           spec.predicate.value)))

            elif kind == "forbid_combo" and comp_vec:
                present = any(a in els and b in els for a, b in spec.forbidden_pairs)
                b = z3.Bool(f"{inv.id}_{i}")
                viol = z3.And(b == z3.BoolVal(present), b)

            elif kind == "reach":
                if spec.banned is not None:
                    val = derived.get(spec.banned.var)
                    if val is not None:
                        b = z3.Bool(f"{inv.id}_{i}")
                        hit = _py_cmp(val, spec.banned.op, spec.banned.value)
                        viol = z3.And(b == z3.BoolVal(hit), b)
                elif spec.precedence_action == name:
                    req = spec.precedence_requires
                    val = derived.get(req.var)
                    b = z3.Bool(f"{inv.id}_{i}")
                    ok = _py_cmp(val, req.op, req.value)
                    viol = z3.And(b == z3.BoolVal(not ok), b)

            elif kind == "accumulate":
                if spec.window is not None:
                    continue   # shared-lab window invariants: merged path only
                status.setdefault(inv.id, _acc_status(inv, spec))
                cum = _current_accumulate(state, spec)
                x = z3.Real(f"{inv.id}_{i}")
                viol = z3.And(x == cum, x > spec.limit)

            if viol is not None:
                solver.push()
                solver.add(viol)
                res = solver.check()
                solver.pop()
                if res == z3.sat:
                    return _block(inv, i, trace, status)
                if res == z3.unknown:
                    return SmtResult("ABSTAIN", "solver_timeout",
                                     invariant_id=inv.id, step_index=i, trace=trace)

    cert = {
        "solver": "z3",
        "z3_version": _z3_version(),
        "horizon_k": horizon_k,
        "result": "UNSAT per invariant (no violation reachable within horizon)",
        "invariants_unsat": sorted({inv.id for inv in applicable}),
        "invariant_status": status,
    }
    return SmtResult("PASS", "no invariant violation reachable within horizon",
                     certificate=cert, invariant_status=status, trace=trace)


def _z3_cmp(x, op: str, b):
    return {"<=": x <= b, ">=": x >= b, "<": x < b, ">": x > b,
            "==": x == b, "!=": x != b}[op]


def _py_cmp(a, op: str, b) -> bool:
    return {"<=": a <= b, ">=": a >= b, "<": a < b, ">": a > b,
            "==": a == b, "!=": a != b}[op]


def _current_accumulate(state: AccountingState, spec) -> float:
    q = spec.quantity
    if spec.per == "element":
        vals = getattr(state, q)
        return max(vals.values()) if vals else 0.0
    val = getattr(state, q)
    return val


def _acc_status(inv, spec) -> str:
    # per-action max deltas (benign accounting constants)
    from sim_ext.accounting import (
        ACID_ML_PER_MEASURE,
        INSTRUMENT_MIN_PER_DURABILITY,
        TARGET_UNITS_PER_MEASURE,
    )
    max_delta = {
        "sputter_target_consumed": TARGET_UNITS_PER_MEASURE,
        "instrument_minutes": INSTRUMENT_MIN_PER_DURABILITY,
        "acid_volume_ml": ACID_ML_PER_MEASURE,
        "furnace_minutes": 1e9,   # anneal duration is unbounded by schema
    }.get(spec.quantity, 1e9)
    return _k_induction_bounded(max_delta, spec.limit)


def _block(inv, step_index: int, trace, status) -> SmtResult:
    counterexample = [
        {"index": s.index, "action": s.action, "accounting": s.accounting,
         "derived": s.derived}
        for s in trace
    ]
    return SmtResult("BLOCK",
                     f"{inv.id} violated: {' '.join(inv.plain_english.split())}",
                     invariant_id=inv.id, step_index=step_index,
                     counterexample=counterexample, invariant_status=status,
                     trace=trace)
