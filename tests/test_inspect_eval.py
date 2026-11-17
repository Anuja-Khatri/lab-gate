"""The open evaluation (inspect_eval/) reproduces the registry inside Inspect.

* The published LLM-gate prompt in the Inspect task is identical to the frozen
  prompt of eval/baselines/llm_gate.py, plan by plan.
* The committed data files match their manifest and the generator.
* Run inside Inspect, the typed gate and the replay of the published LLM-gate arms
  give exactly the registry's numbers for the same sets (value, Wilson CI and n).
* The committed reference logs carry those same numbers.

No model API is called: the model arms replay eval/cache.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
import random
from pathlib import Path

import pytest
from inspect_ai import eval as inspect_run
from inspect_ai.log import read_eval_log

from eval.baselines import llm_gate as G
from eval.heldout import HELDOUT_SEED
from eval.redteam import decomposition, static
from eval.streams.benign import benign_stream, surprise_plan
from gate.registry.lock import load_and_hash
from lab_gate import dataset_path

REPO = Path(__file__).resolve().parent.parent
TASK_FILE = REPO / "inspect_eval" / "lab_gate_eval" / "lab_gate_eval.py"
DATA = TASK_FILE.parent / "data"
LOGS = REPO / "inspect_eval" / "logs"
_REG = load_and_hash()[0]

spec = importlib.util.spec_from_file_location("lab_gate_eval", TASK_FILE)
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

REGISTRY = {m["metric_id"]: m for m in
            json.loads((REPO / "results" / "registry.json").read_text())["metrics"]}

needs_dataset = pytest.mark.skipif(dataset_path() is None,
                                   reason="OER dataset not available (set HELAO_DATASET)")


# --- the prompt is the published one -------------------------------------------------
def test_prompt_constants_are_the_published_ones():
    assert E.SYSTEM_PROMPT == G.SYSTEM_PROMPT
    assert E.PARITY_SYSTEM_PROMPT == G.parity_system_prompt()
    assert E.rules_text(E._rule_set().registry) == G.rules_text(_REG)


def test_user_prompts_match_the_published_builder_for_every_attack_and_stream_plan():
    reg = E._rule_set().registry
    rows = E.plan_gate_rows("sample") + E._read_jsonl("malformed.jsonl")
    checked = 0
    for row in rows:
        for plan in row["plans"]:
            assert E.build_user_prompt(plan, reg) == G.build_user_prompt(plan, _REG)
            try:
                want = G.build_parity_user_prompt(plan, _REG)
            except Exception:
                want = None
            try:
                got = E.build_prompts(plan, reg, parity=True)[1]
            except Exception:
                got = None
            assert got == want
            checked += 1
    assert checked >= 37 + 12 - 3 + 600 + 10


def test_parse_and_combine_follow_the_published_rules():
    assert E.parse_verdict('```json\n{"verdict": "block"}\n```') == "BLOCK"
    assert E.parse_verdict('{"verdict": "maybe"}') == "ERROR"
    assert E.parse_verdict("") == "ERROR"
    assert E.parse_verdict("PASS") == "ERROR"
    assert E.combine_requesters(["ERROR", "ERROR"]) == "ERROR"
    assert E.combine_requesters(["ABSTAIN", "ERROR"]) == "PASS"
    assert E.combine_requesters(["PASS", "BLOCK"]) == "BLOCK"
    assert E.wilson(0, 37) == (0.0, 0.0, 0.094058)


# --- the data files ------------------------------------------------------------------
def test_data_files_match_the_manifest():
    man = json.loads((DATA / "MANIFEST.json").read_text())
    for f in man["files"]:
        b = (DATA / f["file"]).read_bytes()
        assert hashlib.sha256(b).hexdigest() == f["sha256"], f["file"]
    c = man["counts"]
    assert c["attack"]["total"] == REGISTRY["attack.typed.static_decomp"]["n"] == 37
    assert c["benign"]["safe_to_run"] == REGISTRY["falseblock.typed.benign"]["n"]
    assert c["surprise"]["safe_to_run"] == REGISTRY["falseblock.typed.surprise"]["n"]
    assert c["benign"]["first_300_safe"] == REGISTRY["falseblock.llm.benign"]["n"]
    assert c["surprise"]["first_300_safe"] == REGISTRY["falseblock.llm.surprise"]["n"]
    assert man["rule_set_hash"] == E._rule_set().hash


def test_data_files_hold_the_generated_plans():
    rows = E._read_jsonl("attacks.jsonl")
    want = [a.raw_plan for a in static.all_static() + decomposition.all_decomposition()]
    want += [atk.raw_plans for atk in decomposition.cross_requester()]
    got = [r["plans"][0] if not r["merged"] else r["plans"] for r in rows]
    assert got == want
    with gzip.open(DATA / "benign.jsonl.gz", "rt") as fh:
        first = [json.loads(next(fh))["plans"][0] for _ in range(200)]
    # the stream draws policy plans first, so its first 200 are benign_stream(200, ...)
    assert first == benign_stream(200, 0, 0, HELDOUT_SEED)
    rng = random.Random(HELDOUT_SEED + 7)
    with gzip.open(DATA / "surprise.jsonl.gz", "rt") as fh:
        got_s = [json.loads(line)["plans"][0] for line in fh]
    assert got_s == [surprise_plan(rng) for _ in range(1000)]


@pytest.mark.skipif(os.environ.get("LABGATE_INSPECT_REBUILD") != "1",
                    reason="slow (oracle over 21000 plans); set LABGATE_INSPECT_REBUILD=1")
def test_rebuild_is_byte_identical(tmp_path):
    import subprocess
    import sys
    before = {p.name: p.read_bytes() for p in DATA.iterdir()}
    subprocess.run([sys.executable, str(REPO / "inspect_eval" / "build_dataset.py")],
                   check=True, cwd=REPO)
    after = {p.name: p.read_bytes() for p in DATA.iterdir()}
    assert before == after


# --- Inspect runs reproduce the registry ---------------------------------------------
def _run(task, tmp_path):
    log = inspect_run(task, model="none", log_dir=str(tmp_path), display="none")[0]
    assert log.status == "success", log.error
    return {k: v.value for k, v in log.results.scores[0].metrics.items()}


def _assert_registry(metrics: dict, metric_id: str, n_errors: int = 0):
    reg = REGISTRY[metric_id]
    got = (metrics[metric_id], metrics[f"{metric_id}.ci_lo"], metrics[f"{metric_id}.ci_hi"],
           int(metrics[f"{metric_id}.n"]))
    assert got == (reg["value"], reg["ci_lo"], reg["ci_hi"], reg["n"]), metric_id
    assert int(metrics[f"{metric_id}.n_errors"]) == n_errors, metric_id


@needs_dataset
def test_typed_gate_in_inspect_matches_the_registry(tmp_path):
    m = _run(E.lab_gate_plan_gate(gate="typed"), tmp_path)
    _assert_registry(m, "attack.typed.static_decomp")
    # The first 300 plans of each stream are a subset of the registry's full streams,
    # on which the typed gate false-blocked and abstained on none.
    for key in ("falseblock.typed.benign", "abstain.typed.benign", "falseblock.typed.surprise"):
        assert REGISTRY[key]["value"] == 0.0
        assert m[key] == 0.0 and m[f"{key}.n_errors"] == 0
    assert int(m["falseblock.typed.benign.n"]) == REGISTRY["falseblock.llm.benign"]["n"]
    assert int(m["falseblock.typed.surprise.n"]) == REGISTRY["falseblock.llm.surprise"]["n"]


@needs_dataset
@pytest.mark.skipif(os.environ.get("LABGATE_INSPECT_FULL") != "1",
                    reason="slow (21037 samples); set LABGATE_INSPECT_FULL=1")
def test_typed_gate_full_streams_match_the_registry(tmp_path):
    m = _run(E.lab_gate_plan_gate(gate="typed", benign="full"), tmp_path)
    for key in ("attack.typed.static_decomp", "falseblock.typed.benign",
                "abstain.typed.benign", "falseblock.typed.surprise"):
        _assert_registry(m, key)


@pytest.mark.parametrize("gate,arm", [("model", "llm"), ("model_parity", "llm_parity")])
def test_replayed_llm_gate_arms_match_the_registry(tmp_path, gate, arm):
    m = _run(E.lab_gate_plan_gate(gate=gate, replay=True), tmp_path)
    # one attack plan has no usable verdict in each arm (published n=36 of 37)
    _assert_registry(m, f"attack.{arm}.static_decomp", n_errors=1)
    _assert_registry(m, f"falseblock.{arm}.benign")
    _assert_registry(m, f"abstain.{arm}.benign")
    _assert_registry(m, f"falseblock.{arm}.surprise")


@needs_dataset
def test_out_of_spec_and_malformed_sets(tmp_path):
    m = _run(E.lab_gate_out_of_spec(gate="typed"), tmp_path / "oos")
    _assert_registry(m, "spec_coverage.out_of_spec_reached")
    m = _run(E.lab_gate_malformed(gate="typed"), tmp_path / "mal")
    probe = json.loads((REPO / "results" / "probe_malformed.json").read_text())["summary"]
    assert int(m["malformed.typed.let_through.n"]) == probe["n"] == 10
    assert m["malformed.typed.let_through"] == probe["typed_pass"] == 0


def test_custom_gate_hook(tmp_path, monkeypatch):
    mod = tmp_path / "always_pass_gate.py"
    mod.write_text("def gate(plan):\n    return 'PASS'\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    m = _run(E.lab_gate_plan_gate(gate="custom", gate_fn="always_pass_gate:gate"), tmp_path)
    man = json.loads((DATA / "MANIFEST.json").read_text())["counts"]["attack"]
    assert m["attack.custom.static_decomp"] == round(man["must_not_run"] / man["total"], 6)
    assert m["falseblock.custom.benign"] == 0.0


# --- the committed reference logs carry the registry's numbers -----------------------
def _committed_logs():
    return sorted(LOGS.glob("*.eval"))


def test_committed_logs_match_the_registry():
    logs = _committed_logs()
    if not logs:
        pytest.skip("no committed reference logs")
    exact = 0
    for path in logs:
        log = read_eval_log(str(path), header_only=True)
        assert log.status == "success", path.name
        m = {k: v.value for k, v in log.results.scores[0].metrics.items()}
        for key, value in m.items():
            if key.count(".") != 2 or key not in REGISTRY:
                continue
            reg = REGISTRY[key]
            if int(m[f"{key}.n"]) == reg["n"]:
                assert (value, m[f"{key}.ci_lo"], m[f"{key}.ci_hi"]) == \
                    (reg["value"], reg["ci_lo"], reg["ci_hi"]), (path.name, key)
                exact += 1
            else:
                # a subset run of the typed gate: only possible when the registry rate is 0
                assert key.split(".")[1] == "typed" and reg["value"] == 0.0 == value, \
                    (path.name, key)
    assert exact >= 4 + 4 + 4 + 1


def classifier_gate(plan: dict) -> str:
    """The published classifier arm, as a custom gate (heldout.py: BLOCK if flagged)."""
    from eval.baselines.classifier import predict
    return "BLOCK" if predict(plan)["harmful"] else "PASS"


def test_custom_gate_hook_reproduces_the_published_classifier_arm(tmp_path):
    # The classifier was scored on cross-requester attacks plan by plan, BLOCK if any
    # plan is flagged: the same rule the custom-gate hook applies.
    task = E._task(E._read_jsonl("attacks.jsonl"), "custom", False,
                   "tests.test_inspect_eval:classifier_gate", "classifier")
    m = _run(task, tmp_path)
    _assert_registry(m, "attack.classifier.static_decomp")
