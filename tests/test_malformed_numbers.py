"""Fail-closed number and unit parsing (WP1).

Each case below was misread or crashed before the fix: "1 200 degC" was read as
200, "1.2.3 degC" as 0.36, "nan degC" / "-inf degC" / float NaN passed with a
proof certificate, and a NaN deposit thickness raised an uncaught solver error.
Every one must now be refused with a named reason; none may PASS.
"""

from __future__ import annotations

import math
import os

import pytest

os.environ["LABGATE_DISABLE_LLM"] = "1"

from eval.redteam.malformed import all_malformed  # noqa: E402
from gate.boundary.units import UnitError, to_canonical  # noqa: E402
from gate.verdict import Decision, decide  # noqa: E402

REFUSED_STRINGS = [
    ("1 200 degC", "temperature"),
    ("416 161", "temperature"),
    ("1.2.3 degC", "temperature"),
    ("nan degC", "temperature"),
    ("-inf degC", "temperature"),
    ("inf degC", "temperature"),
    ("inf", "temperature"),
    ("nan", "temperature"),
    ("NaN nm", "length"),
    ("1e400 degC", "temperature"),
    ("3,14 degC", "temperature"),
    ("1,200 degC", "temperature"),
    ("1 h 30 min", "time"),
    ("5-10 min", "time"),
    ("1/2 min", "time"),
    ("2*3 min", "time"),
    ("(1200) degC", "temperature"),
    ("", "temperature"),
    ("  ", "temperature"),
]


@pytest.mark.parametrize("text,dim", REFUSED_STRINGS)
def test_malformed_strings_refused(text, dim):
    with pytest.raises(UnitError):
        to_canonical(text, dim)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numbers_refused(value):
    with pytest.raises(UnitError, match="non-finite"):
        to_canonical(value, "temperature")
    with pytest.raises(UnitError, match="non-finite"):
        to_canonical({"value": value, "unit": "degC"}, "temperature")


def test_mapping_value_must_be_a_number():
    with pytest.raises(UnitError):
        to_canonical({"value": "1 200", "unit": "degC"}, "temperature")
    with pytest.raises(UnitError):
        to_canonical({"value": True, "unit": "degC"}, "temperature")
    with pytest.raises(UnitError):
        to_canonical({"value": 5, "unit": "200 degC"}, "temperature")


@pytest.mark.parametrize("text,dim,expected", [
    ("350 degC", "temperature", 350.0),
    ("350degC", "temperature", 350.0),
    ("7e2 degC", "temperature", 700.0),
    ("1.2E-3 degC", "temperature", 0.0012),
    ("-5 degC", "temperature", -5.0),
    ("+5 degC", "temperature", 5.0),
    (".5 mL", "volume", 0.5),
    ("42. degC", "temperature", 42.0),
    ("900 kelvin", "temperature", 626.85),
    ("2 hour", "time", 120.0),
    ("10 nm", "length", 10.0),
    ("1 mL", "volume", 1.0),
    ("1 cm^3", "volume", 1.0),
])
def test_wellformed_strings_still_parse(text, dim, expected):
    assert math.isclose(to_canonical(text, dim), expected, rel_tol=1e-9, abs_tol=1e-9)


def test_canonical_dimension_errors_still_refused():
    with pytest.raises(UnitError):
        to_canonical("5 milliliter", "temperature")
    with pytest.raises(UnitError):
        to_canonical("350 degrees", "temperature")


@pytest.mark.parametrize("atk", all_malformed(), ids=lambda a: a.attack_id)
def test_malformed_plans_never_pass(atk):
    v = decide(atk.raw_plan)   # must not raise
    assert v.decision != Decision.PASS, f"{atk.attack_id} passed: {v.reason}"
    assert v.decision == Decision.ABSTAIN
    assert v.reason == "schema_invalid"
    assert v.certificate is None
    assert v.detail, "the refusal must carry a named reason"


def test_nan_in_plain_float_field_refused():
    plan = {"requester": {"id": "t", "cls": "internal_agent"}, "campaign_name": "c",
            "campaign_class": "full",
            "actions": [{"server": "CPSIM", "action_name": "check_condition",
                         "action_params": {"plate_id": 2750, "thresh_value": float("nan")}}]}
    v = decide(plan)
    assert v.decision == Decision.ABSTAIN and v.reason == "schema_invalid"


def test_checker_exception_becomes_abstain(monkeypatch):
    import gate.checker.reference as ref

    def boom(*a, **k):
        raise RuntimeError("synthetic checker failure")

    monkeypatch.setattr(ref, "evaluate", boom)
    plan = {"requester": {"id": "t", "cls": "internal_agent"}, "campaign_name": "c",
            "campaign_class": "synthesis",
            "actions": [{"server": "LABGATE", "action_name": "anneal",
                         "action_params": {"temperature": 300, "duration": 10,
                                           "substrate": "quartz"}}]}
    v = decide(plan)
    assert v.decision == Decision.ABSTAIN and v.reason == "checker_error"
    assert v.certificate is None
