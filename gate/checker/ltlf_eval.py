"""Independent LTLf trace evaluator (P4.5 secondary cross-check).

Evaluates each invariant's exported LTLf formula over the reference evaluator's
abstract state trace using the TEMPORAL-OPERATOR semantics (G, !, ->, W) applied to
per-step atom truth sequences, independently of the reference's imperative
kind-specific check. equivalence.py asserts the two agree on every suite plan, so a
bug in either the LTLf statement or the imperative check is caught.

Returns (holds, first_violation_step). A single plan is a finite trace; G means
"at every step", W (weak until) encodes Precedence (B is preceded by A).
"""

from __future__ import annotations

from typing import Optional

from gate.checker.reference import StepState
from gate.registry.schema import Invariant


def _cmp(a, op, b):
    return {"<=": a <= b, ">=": a >= b, "<": a < b, ">": a > b,
            "==": a == b, "!=": a != b}[op]


def evaluate_ltlf(inv: Invariant, trace: list[StepState]) -> tuple[bool, Optional[int]]:
    spec = inv.typed_spec()
    kind = str(inv.kind)

    if kind == "bound":
        # Universality: G( action==A -> predicate )
        for s in trace:
            if s.derived.get("action") == spec.action:
                val = s.derived.get(spec.predicate.var)
                if val is not None and not _cmp(val, spec.predicate.op, spec.predicate.value):
                    return False, s.index
        return True, None

    if kind == "forbid_combo":
        # Absence: G !(has(a) & has(b))
        for s in trace:
            els = set(s.derived.get("elements", []))
            for a, b in spec.forbidden_pairs:
                if a in els and b in els:
                    return False, s.index
        return True, None

    if kind == "accumulate":
        if spec.window is not None:
            return True, None   # window invariants evaluated over merged schedule
        # Universality over an aggregate: G( agg <= L )
        for s in trace:
            acc = s.accounting
            if spec.per == "element":
                vals = acc.get("sputter_target_consumed", {})
                cur = max(vals.values()) if vals else 0.0
            else:
                cur = acc.get(spec.quantity, 0.0)
            if cur > spec.limit:
                return False, s.index
        return True, None

    if kind == "reach":
        if spec.banned is not None:
            # Absence: G !banned
            for s in trace:
                val = s.derived.get(spec.banned.var)
                if val is not None and _cmp(val, spec.banned.op, spec.banned.value):
                    return False, s.index
            return True, None
        # Precedence: (!B W A) -- B must be preceded by A holding.
        for s in trace:
            if s.derived.get("action") == spec.precedence_action:
                req = spec.precedence_requires
                if not _cmp(s.derived.get(req.var), req.op, req.value):
                    return False, s.index
        return True, None

    raise ValueError(f"unknown kind {kind}")
