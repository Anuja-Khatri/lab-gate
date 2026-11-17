"""The `lab-gate` command: verdict output, --json, exit codes, examples, version."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from gate.registry.lock import load_and_hash

REPO = Path(__file__).resolve().parent.parent
EX = REPO / "examples"
SEED_HASH = load_and_hash()[1]


def run(*args: str, env_extra: dict | None = None, cwd: Path | None = None):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO)] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "lab_gate", *args], capture_output=True,
                          text=True, env=env, cwd=cwd or REPO, timeout=120)


@pytest.mark.parametrize("plan,code,word", [
    ("plan_pass.json", 0, "PASS"),
    ("plan_block.json", 1, "BLOCK"),
    ("plan_abstain.json", 2, "ABSTAIN"),
])
def test_check_exit_codes_and_human_output(plan, code, word):
    p = run("check", str(EX / plan), "--rules", str(EX / "rules.yaml"))
    assert p.returncode == code, p.stderr
    assert f"verdict:   {word}" in p.stdout
    assert SEED_HASH in p.stdout
    if word == "PASS":
        assert "certificate (proof):" in p.stdout
    if word == "BLOCK":
        assert "counterexample (rule I3b first violated at step 4)" in p.stdout
        assert "furnace_minutes=300.0   <- violation" in p.stdout
    if word == "ABSTAIN":
        assert "unknown_substrate" in p.stdout


@pytest.mark.parametrize("plan,code,word", [
    ("plan_pass.json", 0, "PASS"),
    ("plan_block.json", 1, "BLOCK"),
    ("plan_abstain.json", 2, "ABSTAIN"),
])
def test_check_json(plan, code, word):
    p = run("check", str(EX / plan), "--rules", str(EX / "rules.yaml"), "--json")
    assert p.returncode == code, p.stderr
    out = json.loads(p.stdout)
    assert out["verdict"] == word
    assert out["rule_set_hash"] == SEED_HASH
    assert out["lab_gate_version"] == "1.0.0"
    assert set(out) >= {"verdict", "reason", "detail", "rule_set_hash", "plan_hash",
                        "certificate", "counterexample", "horizon_k"}
    if word == "BLOCK":
        assert out["counterexample"] and out["certificate"]["violated_invariant"] == "I3b"


def test_default_rules_are_the_seed_rules():
    p = run("check", str(EX / "plan_block.json"), "--json")
    assert p.returncode == 1
    assert json.loads(p.stdout)["rule_set_hash"] == SEED_HASH


@pytest.mark.parametrize("args", [
    (),                                   # no command
    ("check",),                           # missing plan
    ("check", "nope.json"),               # missing file
    ("check", "examples/plan_pass.json", "--rules", "nope.yaml"),
    ("check", "examples/plan_pass.json", "--bogus"),
    ("check", "examples/plan_pass.json", "--horizon", "0"),
    ("frobnicate",),
])
def test_usage_errors_exit_64(args):
    p = run(*args)
    assert p.returncode == 64, (p.returncode, p.stdout, p.stderr)


def test_invalid_plan_and_rules_files_exit_64(tmp_path):
    (tmp_path / "p.json").write_text("[]")
    assert run("check", str(tmp_path / "p.json")).returncode == 64
    bad = (EX / "rules.yaml").read_text().replace("var: predicted_erhe_v", "var: typo")
    (tmp_path / "r.yaml").write_text(bad)
    p = run("check", str(EX / "plan_pass.json"), "--rules", str(tmp_path / "r.yaml"))
    assert p.returncode == 64
    assert "unknown variable 'typo'" in p.stderr


def test_version():
    p = run("version")
    assert p.returncode == 0
    assert p.stdout.strip() == "lab-gate 1.0.0"


def test_examples_command_writes_the_shipped_files(tmp_path):
    p = run("examples", str(tmp_path))
    assert p.returncode == 0, p.stderr
    for name in ("rules.yaml", "plan_pass.json", "plan_block.json", "plan_abstain.json"):
        assert (tmp_path / name).read_bytes() == (EX / name).read_bytes()
    # refuses to overwrite without --force
    assert run("examples", str(tmp_path)).returncode == 64
    assert run("examples", str(tmp_path), "--force").returncode == 0
    # and the written files reproduce the documented verdicts from that directory
    q = run("check", "plan_block.json", "--rules", "rules.yaml", cwd=tmp_path)
    assert q.returncode == 1


def test_missing_dataset_warns_and_abstains(tmp_path):
    p = run("check", str(EX / "plan_measure.json"),
            env_extra={"HELAO_DATASET": str(tmp_path / "absent.pzstd")})
    assert p.returncode == 2
    assert "lab-gate fetch-data" in p.stderr
    assert "checker_error" in p.stdout
