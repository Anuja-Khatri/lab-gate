"""Reference plan checker (P4.1): a pure-Python LTLf-over-trace evaluator.

Given a typed plan (ParsedPlan) and the registry, step through the plan building an
abstract state trace (the R-06 accounting state plus native/derived per-step
variables), evaluate every applicable invariant as its LTLf semantics over the
finite trace, and return PASS / BLOCK (first violating step + the full prefix) /
ABSTAIN. This is the independent oracle the SMT encoder (smt.py) is checked against
(equivalence.py, P4.5). It depends only on the typed plan: no free text.

Abstract state variables available to predicates (docs/METHODS.md):
  action                               current action name (str)
  predicted_erhe_v                     surrogate potential for the action's comp (I1)
  anneal_temp_over_limit               anneal temperature > substrate limit (I3)
  sample_qc_passed                     the durability sample passed prior screening (I5)
  action_outside_campaign_capability   action not in the campaign class's set (I8)
  partner_element_not_allowed          external-partner comp uses a non-allowlisted element (ALLOW)
  has(<element>)                       element present in the action's comp_vec (I4)
Accumulated quantities come from sim_ext.accounting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from gate.boundary.schemas import ParsedPlan, TypedAction
from gate.registry.schema import Invariant, Registry
from sim_ext.accounting import (
    AccountingState,
    apply_action,
    elements_of,
    sample_key,
)
from sim_ext.surrogate import gate_predicted_erhe_v

_DECISION_PASS = "PASS"
_DECISION_BLOCK = "BLOCK"
_DECISION_ABSTAIN = "ABSTAIN"

_MEASURE_ACTIONS = {"measure_cp", "durability_test"}
_COMP_ACTIONS = {"measure_cp", "durability_test", "deposit_composition"}


@dataclass
class StepState:
    """The abstract state after applying one action (for the trace/certificate)."""
    index: int
    action: str
    accounting: dict
    derived: dict


@dataclass
class RefResult:
    decision: str
    reason: str
    invariant_id: Optional[str] = None
    step_index: Optional[int] = None
    counterexample: Optional[list] = None      # prefix of steps up to & incl. violation
    trace: list[StepState] = field(default_factory=list)


def _substrate_limit(inv: Invariant, substrate: str) -> Optional[float]:
    limits = inv.extra.get("substrate_limits_degC", {})
    return limits.get(substrate)


def _plate_of(actions: list[TypedAction], upto: int, default: int = 2750) -> int:
    """Loaded plate at step ``upto`` = the last change_plate.plate_id before it."""
    pid = default
    for a in actions[: upto + 1]:
        if a.action_name == "change_plate":
            pid = a.params.plate_id
    return pid


def evaluate(parsed: ParsedPlan, registry: Registry, erhe_provider=None,
             horizon_k: Optional[int] = None) -> RefResult:
    """Evaluate a single typed plan against the registry. See module docstring.

    ``erhe_provider(comp_vec, plate_id) -> float | None`` supplies the potential
    used for I1. The gate passes the surrogate-backed ``gate_predicted_erhe_v``
    (default); the oracle (eval/oracle/oracle.py) passes the ACTUAL dataset value,
    so the two share invariant semantics and differ only in the potential source
    (the measurable model-reality divergence surface). A provider returning None
    means "no potential available" and I1 is not evaluated for that step.

    ``horizon_k``: if set and the plan is longer, the checker ABSTAINs
    (beyond_horizon) to match the SMT bounded semantics (P4.3); if None the full
    plan is evaluated (used by the P3.4 per-invariant semantic tests).
    """
    if erhe_provider is None:
        erhe_provider = gate_predicted_erhe_v
    if not parsed.ok:
        return RefResult(_DECISION_ABSTAIN, parsed.abstain_reason or "unparseable")
    if horizon_k is not None and len(parsed.actions) > horizon_k:
        return RefResult(_DECISION_ABSTAIN, "beyond_horizon", step_index=horizon_k)

    actions = parsed.actions
    req_class = parsed.provenance.requester_class
    campaign_class = parsed.provenance.campaign_class
    allowed_actions = registry.campaign_classes.get(campaign_class)
    allowlist = set(registry.partner_element_allowlist)

    # invariants applicable to this requester class. Capability (I8) and tenant
    # allowlist (ALLOW) gate whether an action may run at all, so they are
    # evaluated before bound/combo/ordering/accumulate invariants.
    _priority = {"I8": 0, "ALLOW": 1}
    applicable = sorted(
        [inv for inv in registry.invariants
         if str(inv.scope) == "any" or str(inv.scope) == req_class],
        key=lambda inv: _priority.get(inv.id, 2),
    )

    state = AccountingState()
    qc_passed: set[str] = set()
    trace: list[StepState] = []

    for i, act in enumerate(actions):
        name = act.action_name
        p = act.params
        params = p.model_dump()
        comp_vec = params.get("comp_vec")
        plate = _plate_of(actions, i)

        # --- I8 capability: unknown class -> ABSTAIN; disallowed action -> BLOCK ---
        if allowed_actions is None:
            return RefResult(_DECISION_ABSTAIN, "unknown_campaign_class",
                             invariant_id="I8", step_index=i, trace=trace)
        action_outside = name not in allowed_actions

        # --- derived vars for this step ---
        predicted = erhe_provider(comp_vec, plate) if comp_vec else None
        anneal_over = False
        if name == "anneal":
            lim = None
            for inv in applicable:
                if inv.id == "I3":
                    lim = _substrate_limit(inv, params.get("substrate", ""))
            if lim is None:
                return RefResult(_DECISION_ABSTAIN, "unknown_substrate",
                                 invariant_id="I3", step_index=i, trace=trace)
            anneal_over = params["temperature"] > lim
        this_sample = sample_key(plate, comp_vec) if comp_vec else None
        sample_qc = (this_sample in qc_passed) if this_sample else False
        els = set(elements_of(comp_vec)) if comp_vec else set()
        partner_bad = (req_class == "external_partner" and name in _COMP_ACTIONS
                       and bool(els - allowlist))

        # --- apply accounting (updates monotone quantities) ---
        apply_action(state, name, params, plate_id=plate,
                     requester_id=parsed.provenance.requester_id,
                     predicted_erhe_v=predicted)
        if name == "measure_cp" and this_sample:
            qc_passed.add(this_sample)

        derived = {
            "action": name,
            "predicted_erhe_v": None if predicted is None else round(predicted, 6),
            "anneal_temp_over_limit": anneal_over,
            "sample_qc_passed": sample_qc,
            "action_outside_campaign_capability": action_outside,
            "partner_element_not_allowed": partner_bad,
            "elements": sorted(els),
        }
        trace.append(StepState(i, name, state.snapshot(), derived))

        # --- per-step invariant checks (first violation -> BLOCK) ---
        for inv in applicable:
            kind = str(inv.kind)
            spec = inv.typed_spec()

            if kind == "bound" and name == spec.action:
                var = spec.predicate.var
                val = derived.get(var)
                if val is not None and not _cmp(val, spec.predicate.op, spec.predicate.value):
                    return _block(inv, i, trace)

            elif kind == "forbid_combo" and comp_vec:
                for a_el, b_el in spec.forbidden_pairs:
                    if a_el in els and b_el in els:
                        return _block(inv, i, trace)

            elif kind == "reach":
                if spec.banned is not None:
                    val = derived.get(spec.banned.var)
                    if val is not None and _cmp(val, spec.banned.op, spec.banned.value):
                        return _block(inv, i, trace)
                elif spec.precedence_action == name:
                    req = spec.precedence_requires
                    val = derived.get(req.var)
                    if not _cmp(val, req.op, req.value):
                        return _block(inv, i, trace)

            elif kind == "accumulate":
                # window (shared-lab) invariants are evaluated over the merged
                # multi-requester schedule by evaluate_merged, not per single plan.
                if spec.window is not None:
                    continue
                if _accumulate_violated(inv, spec, state):
                    return _block(inv, i, trace)

    return RefResult(_DECISION_PASS, "no invariant violated within the plan",
                     trace=trace)


def evaluate_merged(plans: list[ParsedPlan], registry: Registry) -> RefResult:
    """Evaluate the shared-lab window invariants (I7) over a MERGED schedule of
    several requesters' plans (P4.2, P7.3b).

    Actions from all plans are interleaved round-robin (the scheduling order).
    I7 bounds the JOINT instrument minutes over a sliding window of ``window``
    actions, so several requesters each within their own I6 limit can still
    jointly exceed the shared budget. Returns BLOCK with the merged counterexample,
    or PASS if no window invariant is violated (per-plan invariants are checked by
    ``evaluate`` on each plan separately)."""
    window_invs = [
        inv for inv in registry.invariants
        if str(inv.kind) == "accumulate" and inv.typed_spec().window is not None
    ]
    if not window_invs:
        return RefResult(_DECISION_PASS, "no window invariants")

    # round-robin interleave
    merged: list[tuple[ParsedPlan, TypedAction]] = []
    pointers = [0] * len(plans)
    remaining = sum(len(p.actions) for p in plans if p.ok)
    while remaining > 0:
        for pi, plan in enumerate(plans):
            if not plan.ok:
                continue
            if pointers[pi] < len(plan.actions):
                merged.append((plan, plan.actions[pointers[pi]]))
                pointers[pi] += 1
                remaining -= 1

    # per-step instrument-minute deltas over the merged schedule
    deltas: list[float] = []
    trace: list[StepState] = []
    for i, (plan, act) in enumerate(merged):
        pre = AccountingState()
        apply_action(pre, act.action_name, act.params.model_dump(),
                     plate_id=_plate_of(plan.actions, act.index),
                     requester_id=plan.provenance.requester_id)
        deltas.append(pre.instrument_minutes)
        trace.append(StepState(i, act.action_name, {"delta_instrument_minutes": pre.instrument_minutes},
                               {"requester": plan.provenance.requester_id}))
        for inv in window_invs:
            spec = inv.typed_spec()
            w = spec.window
            windowed = sum(deltas[max(0, i - w + 1): i + 1])
            if windowed > spec.limit:
                return _block(inv, i, trace)
    return RefResult(_DECISION_PASS, "merged schedule within shared window budgets",
                     trace=trace)


def _cmp(a, op: str, b) -> bool:
    if op == "<=":
        return a <= b
    if op == ">=":
        return a >= b
    if op == "<":
        return a < b
    if op == ">":
        return a > b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    raise ValueError(f"bad op {op}")


def _accumulate_violated(inv, spec, state: AccountingState) -> bool:
    q = spec.quantity
    if spec.per == "element":
        vals = getattr(state, q)  # dict element -> amount
        return any(v > spec.limit for v in vals.values())
    if spec.per == "requester":
        vals = state.per_requester_minutes
        return any(v > spec.limit for v in vals.values())
    val = getattr(state, q)
    return val > spec.limit


def _block(inv: Invariant, step_index: int, trace: list[StepState]) -> RefResult:
    counterexample = [
        {"index": s.index, "action": s.action, "accounting": s.accounting,
         "derived": s.derived}
        for s in trace
    ]
    return RefResult(
        _DECISION_BLOCK,
        f"{inv.id} violated: {' '.join(inv.plain_english.split())}",
        invariant_id=inv.id,
        step_index=step_index,
        counterexample=counterexample,
        trace=trace,
    )
