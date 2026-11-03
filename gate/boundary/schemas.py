"""Strict typed boundary (P2.1): one pydantic model per action type.

Every model sets ``extra="forbid"`` so an unknown key (a smuggling attempt) is
rejected, not ignored. Every parameter is typed and bounded where physically
meaningful. Physical quantities with units are normalised to canonical units via
``units.to_canonical`` and fail closed on a dimensional mismatch.

Two tiers of action (D-010):
  * NATIVE_ACTIONS: the 10 OERSIM action endpoints (full schema coverage).
  * STANDIN_ACTIONS: benign lab-gate protocol stand-ins (deposit_composition,
    anneal, durability_test) that let invariants I3/I5/I8 model real control
    STRUCTURE with benign quantities. These are NOT helao endpoints.

No free-text field is modelled here: comments and labels are quarantined upstream
(quarantine.py) before a plan is ever parsed into these schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from gate.boundary.quarantine import quarantine_plan
from gate.boundary.units import UnitError, to_canonical
from sim_ext.accounting import ELEMENTS

N_ELEMENTS = len(ELEMENTS)        # 13
COMPOSITION_SUM = 100             # integer atomic-fraction percentages sum to 100


class StopCondition(StrEnum):
    none = "none"
    max_iters = "max_iters"
    max_stdev = "max_stdev"
    max_ei = "max_ei"


class RequesterClass(StrEnum):
    internal_agent = "internal_agent"
    external_partner = "external_partner"
    any = "any"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


def _validate_comp_vec(v: Any) -> list[int]:
    """A comp_vec is exactly N_ELEMENTS integers in [0, 100] summing to 100."""
    if not isinstance(v, (list, tuple)):
        raise ValueError(f"comp_vec must be a list, got {type(v).__name__}")
    if len(v) != N_ELEMENTS:
        raise ValueError(f"comp_vec must have {N_ELEMENTS} entries, got {len(v)}")
    out = []
    for i, x in enumerate(v):
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError(f"comp_vec[{i}]={x!r} must be an int")
        if x < 0 or x > 100:
            raise ValueError(f"comp_vec[{i}]={x} out of range [0,100]")
        out.append(x)
    if sum(out) != COMPOSITION_SUM:
        raise ValueError(f"comp_vec must sum to {COMPOSITION_SUM}, got {sum(out)}")
    return out


def _canon(dimension: str):
    """A reusable before-validator that normalises a quantity to canonical units."""
    def _v(value):
        try:
            return to_canonical(value, dimension)
        except UnitError as exc:
            raise ValueError(str(exc)) from None
    return _v


# --- NATIVE OERSIM action schemas -------------------------------------------
class ChangePlateParams(_Strict):
    plate_id: int = Field(ge=0)


class GetLoadedPlateParams(_Strict):
    pass


class InitializePlateParams(_Strict):
    plate_id: int = Field(ge=0)
    num_random_points: int = Field(default=5, ge=1, le=1000)
    reinitialize: bool = False


class InitializeGlobalParams(_Strict):
    num_random_points: int = Field(default=5, ge=1, le=1000)
    random_seed: int = Field(default=9999, ge=0)


class GetProgressParams(_Strict):
    plate_id: int = Field(ge=0)


class AcquirePointParams(_Strict):
    plate_id: int = Field(ge=0)


class MeasureCPParams(_Strict):
    comp_vec: list[int]
    acquisition_rate: float = Field(default=0.2, gt=0, le=10)

    @field_validator("comp_vec", mode="before")
    @classmethod
    def _cv(cls, v):
        return _validate_comp_vec(v)


class UpdateModelParams(_Strict):
    plate_id: int = Field(ge=0)


class CheckConditionParams(_Strict):
    plate_id: int = Field(ge=0)
    stop_condition: StopCondition = StopCondition.max_iters
    thresh_value: Union[int, float] = 10
    repeat_experiment_name: str = "OERSIM_sub_activelearn"
    repeat_experiment_params: dict = Field(default_factory=dict)
    repeat_experiment_kwargs: dict = Field(default_factory=dict)
    orch_key: str = ""
    orch_host: str = ""
    orch_port: int = Field(default=0, ge=0, le=65535)


class CancelMeasureCPParams(_Strict):
    pass


# --- BENIGN lab-gate protocol stand-ins (D-010) ------------------------------
class DepositCompositionParams(_Strict):
    """Benign stand-in: sputter-deposit a composition (drives I2, I4)."""
    comp_vec: list[int]
    thickness: float = Field(default=1.0)  # canonical: nanometer

    @field_validator("comp_vec", mode="before")
    @classmethod
    def _cv(cls, v):
        return _validate_comp_vec(v)

    @field_validator("thickness", mode="before")
    @classmethod
    def _th(cls, v):
        val = _canon("length")(v)
        if val <= 0:
            raise ValueError(f"thickness must be > 0 nm, got {val}")
        return val


class AnnealParams(_Strict):
    """Benign stand-in: anneal a sample (drives I3). substrate sets the temp limit."""
    temperature: float            # canonical: degree_Celsius
    duration: float = Field(default=30.0)  # canonical: minute
    substrate: str = "quartz"

    @field_validator("temperature", mode="before")
    @classmethod
    def _t(cls, v):
        return _canon("temperature")(v)

    @field_validator("duration", mode="before")
    @classmethod
    def _d(cls, v):
        val = _canon("time")(v)
        if val <= 0:
            raise ValueError(f"duration must be > 0 min, got {val}")
        return val


class DurabilityTestParams(_Strict):
    """Benign stand-in: long-term durability measurement (drives I5, I6)."""
    comp_vec: list[int]
    duration: float = Field(default=60.0)  # canonical: minute

    @field_validator("comp_vec", mode="before")
    @classmethod
    def _cv(cls, v):
        return _validate_comp_vec(v)

    @field_validator("duration", mode="before")
    @classmethod
    def _d(cls, v):
        val = _canon("time")(v)
        if val <= 0:
            raise ValueError(f"duration must be > 0 min, got {val}")
        return val


NATIVE_ACTIONS: dict[str, type[_Strict]] = {
    "change_plate": ChangePlateParams,
    "get_loaded_plate": GetLoadedPlateParams,
    "initialize_plate": InitializePlateParams,
    "initialize_global": InitializeGlobalParams,
    "get_progress": GetProgressParams,
    "acquire_point": AcquirePointParams,
    "measure_cp": MeasureCPParams,
    "update_model": UpdateModelParams,
    "check_condition": CheckConditionParams,
    "cancel_measure_cp": CancelMeasureCPParams,
}

STANDIN_ACTIONS: dict[str, type[_Strict]] = {
    "deposit_composition": DepositCompositionParams,
    "anneal": AnnealParams,
    "durability_test": DurabilityTestParams,
}

ACTION_SCHEMAS: dict[str, type[_Strict]] = {**NATIVE_ACTIONS, **STANDIN_ACTIONS}


class UnknownActionError(ValueError):
    """An action_name outside the schema set (routes to ABSTAIN, not BLOCK)."""


def validate_action_params(action_name: str, params: dict) -> _Strict:
    """Validate one action's params against its schema. Fail closed.

    Raises UnknownActionError if the action type has no schema (-> ABSTAIN),
    or pydantic ValidationError if the params are invalid (-> rejected).
    """
    schema = ACTION_SCHEMAS.get(action_name)
    if schema is None:
        raise UnknownActionError(f"no schema for action {action_name!r}")
    if not isinstance(params, dict):
        raise ValueError(f"params for {action_name} must be a dict")
    return schema.model_validate(params)


# --- plan provenance + typed plan + the parse entrypoint --------------------
@dataclass(frozen=True)
class TypedAction:
    """One validated action in a typed plan. No free-text field is present."""
    index: int
    server: str
    action_name: str
    params: _Strict
    is_native: bool


@dataclass(frozen=True)
class Provenance:
    """Who requested the plan, and the campaign it belongs to (I7, I8, allowlist)."""
    requester_id: str
    requester_class: str      # a RequesterClass value
    campaign_name: str
    campaign_class: str
    window_id: Optional[str] = None


@dataclass
class ParsedPlan:
    """Result of parsing a raw plan at the boundary.

    If ``ok`` is True the plan is fully typed (``actions``) and may proceed to the
    checker. If ``ok`` is False the boundary could not certify the plan as typeable
    and it must ABSTAIN with ``abstain_reason`` (never silently PASS).
    """
    provenance: Provenance
    actions: list[TypedAction]
    quarantined_text: dict
    ok: bool
    abstain_reason: Optional[str] = None
    detail: Optional[str] = None


# Default provenance when a plan omits it (documented): internally-originated.
_DEFAULT_REQUESTER_ID = "system"
_DEFAULT_REQUESTER_CLASS = RequesterClass.internal_agent.value
_DEFAULT_CAMPAIGN_NAME = "default_campaign"
_DEFAULT_CAMPAIGN_CLASS = "activelearn"


def _parse_provenance(clean: dict) -> tuple[Optional[Provenance], Optional[str]]:
    """Validate provenance. Returns (Provenance, None) or (None, reason)."""
    req = clean.get("requester", {})
    if req and not isinstance(req, dict):
        return None, "requester must be a mapping"
    req_id = req.get("id", _DEFAULT_REQUESTER_ID) if req else _DEFAULT_REQUESTER_ID
    req_cls = req.get("cls", _DEFAULT_REQUESTER_CLASS) if req else _DEFAULT_REQUESTER_CLASS
    if not isinstance(req_id, str) or not req_id:
        return None, "requester.id must be a non-empty string"
    if req_cls not in {c.value for c in RequesterClass}:
        return None, f"requester.cls {req_cls!r} is not a valid class"
    campaign_name = clean.get("campaign_name", _DEFAULT_CAMPAIGN_NAME)
    campaign_class = clean.get("campaign_class", _DEFAULT_CAMPAIGN_CLASS)
    window_id = clean.get("window_id")
    if not isinstance(campaign_name, str) or not isinstance(campaign_class, str):
        return None, "campaign_name and campaign_class must be strings"
    if window_id is not None and not isinstance(window_id, str):
        return None, "window_id must be a string or absent"
    return Provenance(req_id, req_cls, campaign_name, campaign_class, window_id), None


def parse_plan(raw_plan: dict) -> ParsedPlan:
    """Quarantine free text, validate provenance, then type every action.

    Total: never raises on plan content (only on a non-dict). Fail-closed outcomes
    are returned as ``ok=False`` with an ABSTAIN reason:
      - provenance_invalid : requester/campaign provenance is malformed
      - out_of_schema_action : an action type has no schema (spec P4.3)
      - schema_invalid : a known action's params fail strict validation
                         (extra key / type confusion / unit mismatch / out of bounds)
    """
    clean, quarantined = quarantine_plan(raw_plan)

    prov, reason = _parse_provenance(clean)
    if prov is None:
        placeholder = Provenance(_DEFAULT_REQUESTER_ID, _DEFAULT_REQUESTER_CLASS,
                                 _DEFAULT_CAMPAIGN_NAME, _DEFAULT_CAMPAIGN_CLASS)
        return ParsedPlan(placeholder, [], quarantined, ok=False,
                          abstain_reason="provenance_invalid", detail=reason)

    raw_actions = clean.get("actions", [])
    if not isinstance(raw_actions, list):
        return ParsedPlan(prov, [], quarantined, ok=False,
                          abstain_reason="schema_invalid",
                          detail="actions must be a list")

    typed: list[TypedAction] = []
    for i, a in enumerate(raw_actions):
        if not isinstance(a, dict):
            return ParsedPlan(prov, [], quarantined, ok=False,
                              abstain_reason="schema_invalid",
                              detail=f"action[{i}] must be a mapping")
        name = a.get("action_name")
        server = a.get("server", "")
        params = a.get("action_params", {})
        try:
            model = validate_action_params(name, params)
        except UnknownActionError as exc:
            return ParsedPlan(prov, [], quarantined, ok=False,
                              abstain_reason="out_of_schema_action",
                              detail=f"action[{i}]: {exc}")
        except (ValidationError, ValueError, TypeError) as exc:
            return ParsedPlan(prov, [], quarantined, ok=False,
                              abstain_reason="schema_invalid",
                              detail=f"action[{i}] ({name}): {str(exc)[:200]}")
        typed.append(TypedAction(
            index=i, server=str(server), action_name=name, params=model,
            is_native=name in NATIVE_ACTIONS,
        ))

    return ParsedPlan(prov, typed, quarantined, ok=True)
