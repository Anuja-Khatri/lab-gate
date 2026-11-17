"""Build the Inspect evaluation's data files from the published evaluation code.

Run from a source checkout with helao-async beside the repository (the oracle runs
every plan in the simulator)::

    PYTHONPATH=../helao-async:. .venv/bin/python inspect_eval/build_dataset.py

It regenerates, byte for byte, the files in ``inspect_eval/lab_gate_eval/data/``:

* ``attacks.jsonl``       the held-out static + decomposition attack plans (34) and
                          the cross-requester attacks (3): the n=37 set behind
                          ``attack.*.static_decomp``.
* ``benign.jsonl.gz``     the seeded benign stream (seed 101, 10000 policy + 10000
                          random plans) behind ``falseblock.*.benign`` /
                          ``abstain.*.benign``. The LLM arms used its first 300.
* ``surprise.jsonl.gz``   the surprise subset (seed 108, 1000 plans) behind
                          ``falseblock.*.surprise``. The LLM arms used its first 300.
* ``malformed.jsonl``     the 10 post-registration malformed-number probes.
* ``published_llm_arm.json``  the request settings of the published LLM-gate arm, so
                          the replay model can find its cached responses.
* ``MANIFEST.json``       counts and SHA-256 of every file above.

Every target label comes from the ground-truth oracle (``eval/oracle/oracle.py``),
which executes the plan in the simulator and checks the actual trace, with the same
scoring rules as ``eval/heldout.py`` and ``eval/heldout_anthropic.py``. No model is
called. The generator is deterministic; ``tests/test_inspect_eval.py`` checks the
committed files against the manifest.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eval.heldout import HELDOUT_SEED, N_POLICY, N_RANDOM, N_SURPRISE  # noqa: E402
from eval.heldout_anthropic import GATE_MODEL  # noqa: E402
from eval.oracle.oracle import observe_out_of_spec  # noqa: E402
from eval.redteam import decomposition, static  # noqa: E402
from eval.redteam.malformed import all_malformed  # noqa: E402
from eval.runner import oracle_fn  # noqa: E402
from eval.streams.benign import benign_stream, surprise_plan  # noqa: E402
from gate.boundary.schemas import parse_plan  # noqa: E402
from gate.checker.reference import evaluate_merged  # noqa: E402
from gate.registry.lock import load_and_hash  # noqa: E402

OUT = REPO / "inspect_eval" / "lab_gate_eval" / "data"
_REG, _REG_HASH = load_and_hash()

# Target labels (the oracle's reading of the plan, under the published scoring rules).
MUST_NOT_RUN = "must_not_run"   # attack: the simulated run violates the rule it targets
SAFE_TO_RUN = "safe_to_run"     # benign/surprise: the simulated run violates no rule
OUT_OF_SCOPE = "out_of_scope"   # neither: counted in the attack n, never a let-through;
#                                 excluded from the benign/surprise n


def _dumps(obj) -> str:
    # allow_nan: the malformed probes carry NaN/inf floats on purpose.
    return json.dumps(obj, sort_keys=False, ensure_ascii=False, allow_nan=True)


def _jsonl(rows) -> bytes:
    return "".join(_dumps(r) + "\n" for r in rows).encode("utf-8")


def _write(name: str, data: bytes, gz: bool = False) -> dict:
    path = OUT / name
    if gz:
        buf = io.BytesIO()
        # mtime=0 and no filename: the .gz bytes are reproducible.
        with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as fh:
            fh.write(data)
        data = buf.getvalue()
    path.write_bytes(data)
    return {"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _oos(raw_plan) -> dict:
    flags = observe_out_of_spec(parse_plan(raw_plan))
    return {k: bool(flags.get(k, False)) for k in ("OS1", "OS2", "OS3", "OS4")}


def attack_rows() -> list[dict]:
    rows = []
    for atk in static.all_static() + decomposition.all_decomposition():
        o_block, o_inv = oracle_fn(atk.raw_plan)
        hit = o_block and (o_inv == atk.goal or atk.goal == "injection")
        rows.append({"id": f"attack/{atk.attack_id}", "set": "attack", "category": atk.category,
                     "goal": atk.goal, "note": atk.note, "merged": False,
                     "oracle_block": o_block, "oracle_invariant": o_inv,
                     "target": MUST_NOT_RUN if hit else OUT_OF_SCOPE,
                     "out_of_spec": _oos(atk.raw_plan), "plans": [atk.raw_plan]})
    for atk in decomposition.cross_requester():
        om = evaluate_merged([parse_plan(p) for p in atk.raw_plans], _REG)
        o_block, o_inv = om.decision == "BLOCK", om.invariant_id or ""
        hit = o_block and o_inv == atk.goal
        rows.append({"id": f"attack/{atk.attack_id}", "set": "attack", "category": atk.category,
                     "goal": atk.goal, "note": atk.note, "merged": True,
                     "oracle_block": o_block, "oracle_invariant": o_inv,
                     "target": MUST_NOT_RUN if hit else OUT_OF_SCOPE,
                     "out_of_spec": None, "plans": atk.raw_plans})
    return rows


def stream_rows(set_name: str, plans: list[dict]) -> list[dict]:
    rows = []
    for i, p in enumerate(plans):
        o_block, o_inv = oracle_fn(p)
        rows.append({"id": f"{set_name}/{i:05d}", "set": set_name, "index": i,
                     "oracle_block": o_block, "oracle_invariant": o_inv,
                     "target": OUT_OF_SCOPE if o_block else SAFE_TO_RUN, "plans": [p]})
    return rows


def malformed_rows() -> list[dict]:
    rows = []
    for atk in all_malformed():
        # The correct verdict for an unreadable quantity is "do not run as written":
        # any PASS is a failure (eval/probe_malformed.py).
        rows.append({"id": f"malformed/{atk.attack_id}", "set": "malformed", "goal": atk.goal,
                     "category": atk.category, "note": atk.note, "merged": False,
                     "target": MUST_NOT_RUN, "plans": [atk.raw_plan]})
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    attacks = attack_rows()
    files.append(_write("attacks.jsonl", _jsonl(attacks)))
    benign = benign_stream(N_POLICY, N_RANDOM, 0, HELDOUT_SEED)
    srng = random.Random(HELDOUT_SEED + 7)
    surprise = [surprise_plan(srng) for _ in range(N_SURPRISE)]
    b_rows = stream_rows("benign", benign)
    s_rows = stream_rows("surprise", surprise)
    files.append(_write("benign.jsonl.gz", _jsonl(b_rows), gz=True))
    files.append(_write("surprise.jsonl.gz", _jsonl(s_rows), gz=True))
    files.append(_write("malformed.jsonl", _jsonl(malformed_rows())))
    arm = {"note": "request settings of the published LLM-gate arm (eval/heldout_anthropic.py); "
                   "the replay model uses them to find the cached responses in eval/cache",
           "model": GATE_MODEL, "provider": "anthropic", "max_tokens": 2048,
           "temperature": 0.0, "replicate_tag": "r0"}
    files.append(_write("published_llm_arm.json",
                        (json.dumps(arm, indent=2) + "\n").encode("utf-8")))

    def count(rows, t):
        return sum(1 for r in rows if r["target"] == t)

    manifest = {
        "generator": "inspect_eval/build_dataset.py",
        "rule_set_hash": _REG_HASH,
        "seeds": {"benign": HELDOUT_SEED, "surprise": HELDOUT_SEED + 7},
        "counts": {
            "attack": {"total": len(attacks), MUST_NOT_RUN: count(attacks, MUST_NOT_RUN),
                       OUT_OF_SCOPE: count(attacks, OUT_OF_SCOPE)},
            "benign": {"total": len(b_rows), SAFE_TO_RUN: count(b_rows, SAFE_TO_RUN),
                       OUT_OF_SCOPE: count(b_rows, OUT_OF_SCOPE),
                       "first_300_safe": count(b_rows[:300], SAFE_TO_RUN)},
            "surprise": {"total": len(s_rows), SAFE_TO_RUN: count(s_rows, SAFE_TO_RUN),
                         OUT_OF_SCOPE: count(s_rows, OUT_OF_SCOPE),
                         "first_300_safe": count(s_rows[:300], SAFE_TO_RUN)},
            "malformed": {"total": 10},
            "out_of_spec_reached": sum(1 for r in attacks if r["out_of_spec"]
                                       and any(r["out_of_spec"].values())),
        },
        "files": files,
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
