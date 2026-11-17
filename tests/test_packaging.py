"""Release consistency: version, shipped copies, bundled model, dataset pin."""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from pathlib import Path

import pytest

import gate
from sim_ext import oersim, surrogate

REPO = Path(__file__).resolve().parent.parent


def test_version_is_single_and_in_changelog():
    meta = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    assert meta["name"] == "lab-gate"
    assert meta["version"] == gate.__version__ == "1.0.0"
    assert meta["scripts"]["lab-gate"] == "lab_gate.cli:main"
    changelog = (REPO / "CHANGELOG.md").read_text()
    assert re.search(rf"^## \[?{re.escape(gate.__version__)}\]?", changelog, re.M)


def test_core_dependencies_stay_minimal():
    deps = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["dependencies"]
    names = {re.split(r"[<>=!~ ]", d)[0].lower() for d in deps}
    assert names == {"pydantic", "pint", "pyyaml", "numpy", "pyzstd", "z3-solver"}


def test_examples_folder_matches_the_packaged_copies():
    assert (REPO / "examples" / "rules.yaml").read_bytes() == \
        (REPO / "gate" / "registry" / "invariants.yaml").read_bytes()
    for p in (REPO / "lab_gate" / "examples").glob("*.json"):
        assert (REPO / "examples" / p.name).read_bytes() == p.read_bytes(), p.name


def test_bundled_surrogate_is_byte_identical_to_results():
    assert surrogate.BUNDLED_CACHE.read_bytes() == surrogate.CACHE.read_bytes()


def test_dataset_pin_matches_the_side_by_side_checkout():
    path = Path(os.environ.get("HELAO_DATASET", oersim.WS_DATASET))
    if not path.exists():
        pytest.skip("helao-async dataset not present")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == oersim.DATASET_SHA256
    assert oersim.DATASET_PIN.startswith("ba910c4")
