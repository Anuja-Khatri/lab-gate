"""P2.5 property-based tests (hypothesis) for schemas and units, plus the
P2 acceptance checks for schema coverage, unknown-key and unit-mismatch rejection.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gate.boundary.schemas import (
    ACTION_SCHEMAS,
    NATIVE_ACTIONS,
    MeasureCPParams,
    parse_plan,
    validate_action_params,
)
from gate.boundary.units import UnitError, to_canonical
from tests.planfactory import random_valid_plan

# The 10 OERSIM-native action types from docs/P0_MEMO.md Section 2.
OERSIM_NATIVE = {
    "change_plate", "get_loaded_plate", "initialize_plate", "initialize_global",
    "get_progress", "acquire_point", "measure_cp", "update_model",
    "check_condition", "cancel_measure_cp",
}


def test_all_oersim_action_types_have_schemas():
    """P2 acceptance: 100% of OERSIM action types have schemas."""
    missing = OERSIM_NATIVE - set(NATIVE_ACTIONS)
    assert not missing, f"OERSIM action types without a schema: {missing}"
    assert OERSIM_NATIVE <= set(ACTION_SCHEMAS)


def test_random_valid_plans_parse():
    rng = random.Random(7)
    for _ in range(300):
        assert parse_plan(random_valid_plan(rng)).ok


# --- unknown keys always rejected (smuggling) -------------------------------
@settings(max_examples=200, deadline=None)
@given(key=st.text(min_size=1, max_size=12).filter(lambda s: s not in {
    "comp_vec", "acquisition_rate"} and s.isidentifier()),
    val=st.one_of(st.integers(), st.text(max_size=5), st.none()))
def test_unknown_key_rejected(key, val):
    cv = [0, 20, 0, 0, 30, 0, 0, 0, 20, 0, 0, 30, 0]
    with pytest.raises(Exception):
        validate_action_params("measure_cp", {"comp_vec": cv, "acquisition_rate": 0.2, key: val})


# --- comp_vec invariants ----------------------------------------------------
@settings(max_examples=200, deadline=None)
@given(vec=st.lists(st.integers(min_value=-5, max_value=120), min_size=0, max_size=20))
def test_comp_vec_rejected_unless_valid(vec):
    ok = (len(vec) == 13 and all(0 <= x <= 100 for x in vec) and sum(vec) == 100)
    if ok:
        m = MeasureCPParams(comp_vec=vec)
        assert m.comp_vec == vec
    else:
        with pytest.raises(Exception):
            MeasureCPParams(comp_vec=vec)


# --- unit normalisation -----------------------------------------------------
def test_unit_canonicalisation_and_mismatch():
    # temperature conversions to canonical degC
    assert abs(to_canonical("350 degC", "temperature") - 350.0) < 1e-6
    assert abs(to_canonical("623.15 kelvin", "temperature") - 350.0) < 1e-2
    assert abs(to_canonical({"value": 350, "unit": "degC"}, "temperature") - 350.0) < 1e-6
    # bare number assumed canonical
    assert to_canonical(30, "time") == 30.0
    # dimensional mismatch fails closed
    for bad in ["5 ml", "5 meter", "5 hertz"]:
        with pytest.raises(UnitError):
            to_canonical(bad, "temperature")
    # unparseable fails closed
    with pytest.raises(UnitError):
        to_canonical("not a quantity", "time")


@settings(max_examples=150, deadline=None)
@given(v=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
def test_volume_roundtrip_liters_to_ml(v):
    # v liters -> v*1000 ml
    assert abs(to_canonical(f"{v} liter", "volume") - v * 1000.0) < 1e-3
