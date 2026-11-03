"""In-process OER active-learning simulator (R-05 fallback).

The full helao-async FastAPI/Bokeh orchestration group cannot launch in this
environment (no conda; uvicorn/bokeh/torch/zmq/boto3 absent; see DECISIONS D-009).
Per R-05 we drive OERSIM directly through Python, preserving its action models and
using the REAL ``oer13_cps`` dataset and the REAL ``calc_eta`` metric. Nothing in
helao-async is modified; it is imported read-only.

What is faithful:
  - the action sequence (change_plate, get_loaded_plate, initialize_plate, then per
    iteration get_loaded_plate / acquire_point / measure_cp / update_model) mirrors
    ``helao/deploy/test/experiments/OERSIM_exp.py`` exactly (cross-checked by
    tests/test_oersim_fidelity.py against the real plan-makers);
  - ``measure_cp`` replays the composition's real stored CP trace and computes the
    real overpotential via ``helao...oer_metrics.calc_eta``.

The single documented bypass: the GP-surrogate acquisition (``acquire_point`` needs
torch) is replaced, for closed-loop simulation and benign-plan generation, by a
SEEDED deterministic sampler over the plate's REAL addressable compositions. The
oracle never needs the GP: it executes a GIVEN plan against the real dataset.

Determinism: with a fixed seed the emitted trace is byte-identical across runs; it
contains only deterministic content (no uuids, no timestamps).
"""

from __future__ import annotations

import json
import os
import pickle
import random
from pathlib import Path
from typing import Optional

import pyzstd

from sim_ext.accounting import AccountingState, apply_action

REPO_ROOT = Path(__file__).resolve().parent.parent          # $WS/lab-gate
WS = REPO_ROOT.parent                                        # $WS
DEFAULT_DATASET = WS / "helao-async/helao/deploy/test/demos/data/oer13_cps.pzstd"


def _calc_eta(cp_dict) -> float:
    """Overpotential from the final 4 s of a CP trace.

    Imports helao-async's real ``calc_eta`` when importable (faithful); otherwise
    uses an identical inline computation (the metric is four lines of arithmetic
    with no heavy dependency, per helao's oer_metrics.py).
    """
    try:
        from helao.deploy.test.drivers.data.oer_metrics import calc_eta
        return calc_eta(cp_dict)
    except Exception:
        OER_POTENTIAL_VRHE = 1.23
        window = 4
        thresh_ts = max(cp_dict["t_s"]) - window
        thresh_idx = min(i for i, v in enumerate(cp_dict["t_s"]) if v > thresh_ts)
        erhes = cp_dict["erhe_v"][thresh_idx:]
        return sum(erhes) / len(erhes) - OER_POTENTIAL_VRHE


def mean_erhe_v(cp_dict, window: float = 4.0) -> float:
    """Mean steady-state potential (V vs RHE) over the final ``window`` seconds.

    This is the instrument-protection quantity for I1: eta = this - 1.23.
    """
    thresh_ts = max(cp_dict["t_s"]) - window
    thresh_idx = min(i for i, v in enumerate(cp_dict["t_s"]) if v > thresh_ts)
    erhes = cp_dict["erhe_v"][thresh_idx:]
    return sum(erhes) / len(erhes)


class InProcessOERSIM:
    """Deterministic in-process driver over the real OER dataset."""

    def __init__(self, dataset_path: Optional[Path] = None):
        path = Path(os.environ.get("HELAO_DATASET", dataset_path or DEFAULT_DATASET))
        if not path.exists():
            raise FileNotFoundError(
                f"OER dataset not found at {path}. Set HELAO_DATASET or ensure "
                f"$WS/helao-async is present (pinned ba910c4)."
            )
        with pyzstd.ZstdFile(str(path), "rb") as fh:
            self.all_data = pickle.load(fh)
        self.elements: list[str] = list(self.all_data["els"])
        self.plates: list[int] = [k for k in self.all_data if k != "els"]
        self.loaded_plate: int = self.plates[0]

    # --- native OERSIM operations -------------------------------------------
    def change_plate(self, plate_id: int) -> bool:
        if plate_id in self.all_data and plate_id != "els":
            self.loaded_plate = plate_id
            return True
        return False

    def addressable(self, plate_id: Optional[int] = None) -> list[tuple]:
        """Sorted list of addressable composition tuples on a plate (real data)."""
        pid = self.loaded_plate if plate_id is None else plate_id
        return sorted(self.all_data[pid].keys())

    def cp_trace(self, comp_vec, plate_id: Optional[int] = None) -> Optional[dict]:
        """Return the real stored CP3 trace for a composition, or None if not
        addressable on the plate."""
        pid = self.loaded_plate if plate_id is None else plate_id
        rec = self.all_data[pid].get(tuple(comp_vec))
        return None if rec is None else rec["CP3"]

    def measure_cp(self, comp_vec, plate_id: Optional[int] = None) -> dict:
        """Execute a simulated CP for ``comp_vec`` and return real observables.

        Returns the actual steady-state potential and overpotential from the
        stored trace. Raises KeyError for a non-addressable composition (same
        contract as the real CPSimExec).
        """
        pid = self.loaded_plate if plate_id is None else plate_id
        cp = self.cp_trace(comp_vec, pid)
        if cp is None:
            raise KeyError(
                f"comp_vec {list(comp_vec)} is not addressable on plate {pid}"
            )
        return {
            "comp_vec": list(comp_vec),
            "actual_erhe_v": mean_erhe_v(cp),
            "actual_eta_vrhe": _calc_eta(cp),
        }

    def acquire_next(self, plate_id: int, rng: random.Random, history: set) -> list[int]:
        """Deterministic stand-in for GP-EI acquisition (documented bypass).

        Picks a real addressable composition not yet measured, uniformly at random
        under the provided seeded RNG. This is NOT the GP policy; it is a seeded
        sampler over the real composition set, used only for closed-loop
        simulation and benign-plan generation.
        """
        comps = [c for c in self.addressable(plate_id) if c not in history]
        if not comps:
            comps = self.addressable(plate_id)
        return list(rng.choice(comps))


def run_activelearn(
    plate_id: int,
    iterations: int,
    seed: int,
    dataset_path: Optional[Path] = None,
    requester_id: Optional[str] = None,
) -> dict:
    """Run one deterministic OERSIM active-learning closed loop in-process.

    Mirrors the OERSIM_sub_load_plate + N x OERSIM_sub_measure_CP action sequence.
    Returns a canonical dict: the ordered action trace and per-step accounting
    snapshots. Deterministic for a fixed (plate_id, iterations, seed).
    """
    sim = InProcessOERSIM(dataset_path)
    rng = random.Random(seed)
    state = AccountingState()
    history: set = set()
    trace: list[dict] = []

    def record(server: str, action_name: str, params: dict, outputs: dict):
        apply_action(
            state,
            action_name,
            params,
            plate_id=sim.loaded_plate,
            requester_id=requester_id,
            actual_erhe_v=outputs.get("actual_erhe_v"),
        )
        trace.append({
            "i": len(trace),
            "server": server,
            "action": action_name,
            "params": params,
            "outputs": {k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in outputs.items()},
            "accounting": state.snapshot(),
        })

    # --- load plate (mirrors OERSIM_sub_load_plate) ---
    sim.change_plate(plate_id)
    record("CPSIM", "change_plate", {"plate_id": plate_id}, {"loaded_plate_id": plate_id})
    record("CPSIM", "get_loaded_plate", {}, {"loaded_plate_id": sim.loaded_plate})
    record("GPSIM", "initialize_plate",
           {"plate_id": sim.loaded_plate, "num_random_points": 5, "reinitialize": False}, {})

    # --- active-learning loop (mirrors OERSIM_sub_measure_CP) ---
    for _ in range(iterations):
        record("CPSIM", "get_loaded_plate", {}, {"loaded_plate_id": sim.loaded_plate})
        comp_vec = sim.acquire_next(sim.loaded_plate, rng, history)
        history.add(tuple(comp_vec))
        record("GPSIM", "acquire_point", {"plate_id": sim.loaded_plate},
               {"feature": comp_vec})
        meas = sim.measure_cp(comp_vec)
        record("CPSIM", "measure_cp", {"comp_vec": comp_vec, "acquisition_rate": 0.2}, meas)
        record("GPSIM", "update_model", {"plate_id": sim.loaded_plate}, {})

    return {
        "config": {"plate_id": plate_id, "iterations": iterations, "seed": seed,
                   "requester_id": requester_id},
        "elements": sim.elements,
        "n_actions": len(trace),
        "trace": trace,
        "final_accounting": state.snapshot(),
    }


def canonical_json(obj) -> str:
    """Canonical serialisation for byte-identity: sorted keys, fixed separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    """`make sim` entry point: run a fixed seeded closed loop and write a trace.

    Usage: python -m sim_ext.oersim <out_path> [plate_id] [iterations] [seed]
    """
    import sys
    args = argv if argv is not None else sys.argv[1:]
    out = Path(args[0]) if args else (REPO_ROOT / "results" / "sim_trace.json")
    plate_id = int(args[1]) if len(args) > 1 else 2750
    iterations = int(args[2]) if len(args) > 2 else 8
    seed = int(args[3]) if len(args) > 3 else 20261103
    result = run_activelearn(plate_id, iterations, seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(canonical_json(result))
    print(f"sim: plate={plate_id} iters={iterations} seed={seed} "
          f"n_actions={result['n_actions']} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
