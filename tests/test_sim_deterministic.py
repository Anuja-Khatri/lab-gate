"""P1 acceptance: the in-process OERSIM closed loop is seeded and byte-identical
across runs, and accounting state is readable at every step for every quantity the
invariants need."""

from __future__ import annotations

from sim_ext.oersim import canonical_json, run_activelearn

SEED = 20261103


def test_byte_identical_across_runs():
    a = canonical_json(run_activelearn(2750, 8, SEED))
    b = canonical_json(run_activelearn(2750, 8, SEED))
    assert a == b, "same (plate, iters, seed) must produce byte-identical traces"


def test_different_seed_differs():
    a = canonical_json(run_activelearn(2750, 8, SEED))
    c = canonical_json(run_activelearn(2750, 8, SEED + 1))
    assert a != c, "a different seed should change the acquisition path"


def test_accounting_readable_every_step():
    result = run_activelearn(2750, 8, SEED)
    required = {
        "sputter_target_consumed", "instrument_minutes", "acid_volume_ml",
        "furnace_minutes", "qc_passed", "per_requester_minutes",
        "last_predicted_erhe_v", "last_actual_erhe_v", "n_measurements", "step",
    }
    assert result["trace"], "trace must be non-empty"
    for step in result["trace"]:
        assert "accounting" in step, f"step {step['i']} missing accounting snapshot"
        assert required <= set(step["accounting"]), (
            f"step {step['i']} accounting missing {required - set(step['accounting'])}"
        )


def test_measurements_update_accounting_monotonically():
    result = run_activelearn(2750, 8, SEED)
    prev_instr = -1.0
    for step in result["trace"]:
        instr = step["accounting"]["instrument_minutes"]
        assert instr >= prev_instr, "instrument minutes must be monotone non-decreasing"
        prev_instr = instr
    # 8 measurements x 10 instrument-min each
    assert result["final_accounting"]["instrument_minutes"] == 80.0
    assert result["final_accounting"]["n_measurements"] == 8
    # total sputter consumption = 8 measures x 1.0 unit
    total = sum(result["final_accounting"]["sputter_target_consumed"].values())
    assert abs(total - 8.0) < 1e-6
