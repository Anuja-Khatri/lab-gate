"""Invariant registry schema (P3.1).

Four invariant kinds, each mapped to a finite-trace linear temporal logic (LTLf)
specification pattern (Dwyer, Avrunin & Corbett, ICSE 1999; De Giacomo & Vardi,
IJCAI 2013). See gate/registry/ltlf.py for the formula renderer.

  bound        single-action parameter/derived-quantity bound   -> Absence / Universality (G !p / G p)
  forbid_combo a set of values that may not co-occur             -> Absence (G !p)
  accumulate   sum/max of a quantity over the plan within limit  -> Universality over an aggregate (G agg<=L)
  reach        a banned state predicate over the state trace,    -> Absence (G !p) or
               incl. protocol ordering (B unless prior predicate)   Precedence (!B W A)

Each invariant declares: id, kind, plain_english, scope (requester classes it
applies to), rationale, source (where the control is grounded), and a strict
kind-specific ``spec``. The ``ltlf`` and ``pattern`` fields are generated.

Predicate mini-language (used by bound/reach), a strict mapping:
  {"var": <state-or-derived var>, "op": "<=|>=|<|>|==|!=", "value": <number|bool|str>}
State/derived variables available to the checker are documented in
docs/METHODS.md and implemented in gate/checker/reference.py.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvariantKind(StrEnum):
    bound = "bound"
    forbid_combo = "forbid_combo"
    accumulate = "accumulate"
    reach = "reach"


class Scope(StrEnum):
    internal_agent = "internal_agent"
    external_partner = "external_partner"
    any = "any"


_OPS = {"<=", ">=", "<", ">", "==", "!="}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Predicate(_Strict):
    """A comparison on a per-step state or derived variable."""
    var: str
    op: str
    value: Union[int, float, bool, str]

    @field_validator("op")
    @classmethod
    def _op(cls, v):
        if v not in _OPS:
            raise ValueError(f"op {v!r} not in {sorted(_OPS)}")
        return v


# --- per-kind specs ---------------------------------------------------------
class BoundSpec(_Strict):
    kind: Literal["bound"] = "bound"
    action: str                     # action type the bound applies to
    predicate: Predicate            # bound on a param/derived quantity of that action


class ForbidComboSpec(_Strict):
    kind: Literal["forbid_combo"] = "forbid_combo"
    subject: Literal["elements"] = "elements"
    scope_unit: Literal["action", "window"] = "action"
    forbidden_pairs: list[list[str]]   # pairs that may not co-occur
    window: Optional[int] = None       # #actions for scope_unit=window


class AccumulateSpec(_Strict):
    kind: Literal["accumulate"] = "accumulate"
    quantity: str                   # accounting key (e.g. instrument_minutes)
    agg: Literal["sum", "max"] = "sum"
    limit: float
    per: Optional[Literal["element", "requester"]] = None
    window: Optional[int] = None    # scheduling window (#actions) for shared budgets


class ReachSpec(_Strict):
    kind: Literal["reach"] = "reach"
    # exactly one of banned / precedence must be set
    banned: Optional[Predicate] = None
    precedence_action: Optional[str] = None     # action B
    precedence_requires: Optional[Predicate] = None  # predicate that must hold before B

    @field_validator("precedence_requires")
    @classmethod
    def _coherent(cls, v, info):
        return v


SpecUnion = Union[BoundSpec, ForbidComboSpec, AccumulateSpec, ReachSpec]

_SPEC_BY_KIND = {
    "bound": BoundSpec,
    "forbid_combo": ForbidComboSpec,
    "accumulate": AccumulateSpec,
    "reach": ReachSpec,
}


class Invariant(_Strict):
    id: str
    kind: InvariantKind
    plain_english: str
    scope: Scope = Scope.any
    rationale: str
    source: str
    spec: dict
    # generated
    ltlf: Optional[str] = None
    pattern: Optional[str] = None
    # for I8 capability exposure and the per-tenant allowlist we carry extra
    # declarative data keyed by campaign class / requester class.
    extra: dict = Field(default_factory=dict)

    @field_validator("spec")
    @classmethod
    def _spec_valid(cls, v, info):
        kind = info.data.get("kind")
        if kind is None:
            return v
        model = _SPEC_BY_KIND[str(kind)]
        parsed = model.model_validate({**v, "kind": str(kind)})
        if str(kind) == "reach":
            has_banned = parsed.banned is not None
            has_prec = parsed.precedence_action is not None
            if has_banned == has_prec:
                raise ValueError(
                    "reach spec must set exactly one of banned / precedence_action"
                )
            if has_prec and parsed.precedence_requires is None:
                raise ValueError("precedence_action requires precedence_requires")
        return v

    def typed_spec(self) -> SpecUnion:
        model = _SPEC_BY_KIND[str(self.kind)]
        return model.model_validate({**self.spec, "kind": str(self.kind)})


class Registry(_Strict):
    version: str
    composition_sum: int = 100
    campaign_classes: dict[str, list[str]] = Field(default_factory=dict)
    partner_element_allowlist: list[str] = Field(default_factory=list)
    invariants: list[Invariant]

    @field_validator("invariants")
    @classmethod
    def _unique_ids(cls, v):
        ids = [inv.id for inv in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate invariant ids")
        return v


def load_registry(path) -> Registry:
    """Load and validate a registry YAML, rendering ltlf/pattern for each invariant."""
    import yaml

    from gate.registry.ltlf import render

    with open(path) as fh:
        data = yaml.safe_load(fh)
    reg = Registry.model_validate(data)
    for inv in reg.invariants:
        pattern, formula = render(inv)
        inv.pattern = pattern
        inv.ltlf = formula
    return reg
