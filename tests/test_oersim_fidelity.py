"""R-05 fidelity: the in-process action sequence matches the REAL helao-async
OERSIM plan-makers, and measure_cp replays the REAL dataset trace.

These tests import helao-async read-only (PYTHONPATH must include $WS/helao-async).
If helao-async is not importable, the tests skip with a clear reason rather than
silently passing.
"""

from __future__ import annotations

import pytest

from sim_ext.oersim import InProcessOERSIM, run_activelearn

helao_exp = pytest.importorskip(
    "helao.deploy.test.experiments.OERSIM_exp",
    reason="helao-async not importable; set PYTHONPATH=$WS/helao-async",
)


def _seq(planned):
    """Extract the (server_name, action_name) sequence from planned actions."""
    out = []
    for a in planned:
        srv = getattr(a, "action_server", None)
        name = getattr(srv, "server_name", None)
        out.append((name, a.action_name))
    return out


def test_measure_cp_action_sequence_matches_real_plan_maker():
    real = _seq(helao_exp.OERSIM_sub_measure_CP(init_random_points=5))
    assert real == [
        ("CPSIM", "get_loaded_plate"),
        ("GPSIM", "acquire_point"),
        ("CPSIM", "measure_cp"),
        ("GPSIM", "update_model"),
    ], f"real OERSIM measure_CP sequence changed: {real}"


def test_inprocess_loop_reproduces_real_sequence():
    real_iter = _seq(helao_exp.OERSIM_sub_measure_CP(init_random_points=5))
    result = run_activelearn(2750, 3, seed=1)
    names = [(s["server"], s["action"]) for s in result["trace"]]
    # drop the load-plate prefix (change_plate, get_loaded_plate, initialize_plate)
    assert names[:3] == [
        ("CPSIM", "change_plate"),
        ("CPSIM", "get_loaded_plate"),
        ("GPSIM", "initialize_plate"),
    ]
    body = names[3:]
    # body is 3 iterations of the real measure_CP sequence
    assert len(body) == 3 * len(real_iter)
    for k in range(3):
        assert body[k * 4:(k + 1) * 4] == real_iter


def test_measure_cp_uses_real_dataset_trace():
    sim = InProcessOERSIM()
    comp = sim.addressable(2750)[0]
    out = sim.measure_cp(comp, 2750)
    # the actual overpotential comes from the real stored CP trace
    assert "actual_eta_vrhe" in out and "actual_erhe_v" in out
    assert out["actual_erhe_v"] > 1.23  # OER potentials exceed the thermodynamic value
    with pytest.raises(KeyError):
        sim.measure_cp([99, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], 2750)  # not addressable
