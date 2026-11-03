"""Predicted-potential surrogate (D-014): the gate's abstract I1 model.

A simple, documented, deterministic per-element linear model of composition ->
mean steady-state potential (V vs RHE), fit on a DEV split of the real dataset's
compositions and cached. The CHECKER uses this prediction for I1
(``predicted_erhe_v``); the ORACLE (Phase 6) uses the ACTUAL trace. The gap between
them is the measurable model-reality divergence surface (HYP-2): a linear model
cannot reproduce the plate-2750 overload spikes, so some compositions the gate
predicts safe are actually overloads, and that is reported, never hidden.

The surrogate is never fit on held-out plan seeds; it is fit on compositions
assigned to the dev split by a deterministic hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pyzstd

from sim_ext.accounting import ELEMENTS
from sim_ext.oersim import DEFAULT_DATASET, mean_erhe_v

CACHE = Path(__file__).resolve().parent.parent / "results" / "surrogate.json"
DEV_FRACTION = 0.8   # share of compositions used to fit (rest are held out)


def _is_dev(plate_id: int, comp_vec: tuple) -> bool:
    key = f"{plate_id}:" + "-".join(map(str, comp_vec))
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16) % 1000
    return h < int(DEV_FRACTION * 1000)


def fit_surrogate(dataset_path: Optional[Path] = None) -> dict:
    """Fit the linear surrogate on dev compositions and write the cache."""
    path = Path(os.environ.get("HELAO_DATASET", dataset_path or DEFAULT_DATASET))
    with pyzstd.ZstdFile(str(path), "rb") as fh:
        data = pickle.load(fh)
    rows, ys = [], []
    for pid in [k for k in data if k != "els"]:
        for comp, rec in data[pid].items():
            if not _is_dev(pid, comp):
                continue
            rows.append([c / 100.0 for c in comp])
            ys.append(mean_erhe_v(rec["CP3"]))
    X = np.array(rows, dtype=float)
    y = np.array(ys, dtype=float)
    # least squares with an intercept column
    A = np.hstack([X, np.ones((len(X), 1))])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    weights = coef[:-1].tolist()
    intercept = float(coef[-1])
    model = {
        "elements": list(ELEMENTS),
        "weights": weights,
        "intercept": intercept,
        "n_fit": len(X),
        "dev_fraction": DEV_FRACTION,
        "note": "linear comp->mean_erhe_v; gate abstract I1 model (D-014). Dev fit only.",
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(model, indent=2) + "\n")
    return model


_MODEL: Optional[dict] = None


def _load_model() -> dict:
    global _MODEL
    if _MODEL is None:
        if not CACHE.exists():
            _MODEL = fit_surrogate()
        else:
            _MODEL = json.loads(CACHE.read_text())
    return _MODEL


def predict_erhe_v(comp_vec) -> float:
    """Linear-surrogate predicted steady-state potential (V vs RHE)."""
    m = _load_model()
    w = m["weights"]
    val = m["intercept"]
    for i, pct in enumerate(comp_vec):
        val += w[i] * (pct / 100.0)
    return float(val)


_DATASET = None


def _actual_lookup(plate_id: int, comp_vec) -> Optional[float]:
    """The measured steady-state potential for an already-characterised composition,
    or None if the composition is novel (not addressable on the plate)."""
    global _DATASET
    if _DATASET is None:
        path = Path(os.environ.get("HELAO_DATASET", DEFAULT_DATASET))
        with pyzstd.ZstdFile(str(path), "rb") as fh:
            _DATASET = pickle.load(fh)
    plate = _DATASET.get(plate_id)
    if plate is None:
        return None
    rec = plate.get(tuple(comp_vec))
    if rec is None:
        return None
    return mean_erhe_v(rec["CP3"])


def gate_predicted_erhe_v(comp_vec, plate_id: Optional[int] = None) -> float:
    """The gate's I1 prediction using its BEST available knowledge (D-015).

    If the composition has already been characterised on the plate (addressable),
    the gate uses its measured steady-state potential (prior-measurement history);
    otherwise it falls back to the linear surrogate. This gives I1 real teeth on
    known-overload compositions and makes every I1 BLOCK replay in the simulator
    (P4.6). Novel compositions the surrogate under-predicts are the residual
    divergence surface, but being non-addressable they cannot be measured, so they
    cannot count as attack success at the oracle (consistent with HYP-1).
    """
    if plate_id is not None:
        actual = _actual_lookup(plate_id, comp_vec)
        if actual is not None:
            return actual
    return predict_erhe_v(comp_vec)


if __name__ == "__main__":
    m = fit_surrogate()
    print(f"surrogate fit on {m['n_fit']} dev compositions; intercept {m['intercept']:.3f}")
