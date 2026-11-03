"""LTLf formula renderer (P3.1).

Renders each invariant as a finite-trace linear temporal logic (LTLf) formula
string together with its Dwyer/Avrunin/Corbett (ICSE 1999) specification-pattern
name. These strings are the human- and machine-readable formal statement of each
invariant; the reference evaluator (gate/checker/reference.py, Phase 4) and the
SMT encoder (gate/checker/smt.py, Phase 4) implement the same semantics over the
plan's finite state trace, and gate/checker/equivalence.py (P4.5) checks that the
rendered formula, evaluated by the reference trace evaluator, agrees with the
kind-specific check.

Operators: G (globally/always), F (eventually), X (next), U (until),
W (weak until). Atomic propositions are comparisons on per-step state variables.

Patterns used:
  bound        -> "Absence" (G !p) or "Universality" (G p)
  forbid_combo -> "Absence" (G !cooccur)
  accumulate   -> "Universality" over an aggregate state variable (G agg<=L)
  reach banned -> "Absence" (G !banned)
  reach order  -> "Precedence" (!B W A): B does not occur unless A held earlier
"""

from __future__ import annotations

from gate.registry.schema import Invariant

_NEG = {"<=": ">", ">=": "<", "<": ">=", ">": "<=", "==": "!=", "!=": "=="}


def _atom(var: str, op: str, value) -> str:
    v = "true" if value is True else "false" if value is False else repr(value)
    return f"({var} {op} {v})"


def render(inv: Invariant) -> tuple[str, str]:
    """Return (pattern_name, ltlf_formula_string) for an invariant."""
    spec = inv.typed_spec()
    kind = str(inv.kind)

    if kind == "bound":
        # whenever the action occurs, the bounded predicate must hold:
        # Universality G( action -> predicate ), equivalently Absence of violation.
        p = _atom(spec.predicate.var, spec.predicate.op, spec.predicate.value)
        act = f"(action == {spec.action!r})"
        return "Universality", f"G( {act} -> {p} )"

    if kind == "forbid_combo":
        pairs = " | ".join(
            f"(has({a}) & has({b}))" for a, b in spec.forbidden_pairs
        )
        if spec.scope_unit == "action":
            return "Absence", f"G !( {pairs} )"
        # window variant: never co-occurring within a sliding window of W actions
        return "Absence", f"G !( within[{spec.window}]( {pairs} ) )"

    if kind == "accumulate":
        agg = f"{spec.agg}({spec.quantity}" + (
            f" per {spec.per}" if spec.per else ""
        ) + (f" over window[{spec.window}]" if spec.window else "") + ")"
        return "Universality", f"G( {agg} <= {spec.limit} )"

    if kind == "reach":
        if spec.banned is not None:
            b = _atom(spec.banned.var, spec.banned.op, spec.banned.value)
            return "Absence", f"G !{b}"
        # Precedence: B is preceded by A.  !B W A  (B cannot happen until A holds)
        req = _atom(spec.precedence_requires.var,
                    spec.precedence_requires.op,
                    spec.precedence_requires.value)
        b = f"(action == {spec.precedence_action!r})"
        return "Precedence", f"( !{b} W {req} )"

    raise ValueError(f"unknown kind {kind!r}")
