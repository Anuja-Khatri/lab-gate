"""Run the malformed-number probe suite (offline, deterministic, no API calls).

Writes results/probe_malformed.json: for each probe plan, the typed gate's
decision, reason and detail, whether a certificate was issued, the classifier
baseline's decision, and the oracle's reading. The suite is post-registration and
reported separately from the preregistered static+decomposition suites; see
eval/redteam/malformed.py and docs/CORRECTIONS.md.

Exit status is nonzero if the typed gate PASSes any probe or crashes on one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("LABGATE_DISABLE_LLM", "1")

from eval.baselines.classifier import predict as clf_predict  # noqa: E402
from eval.redteam.malformed import all_malformed  # noqa: E402
from gate.boundary.schemas import parse_plan  # noqa: E402
from gate.verdict import decide  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "probe_malformed.json"


def _oracle(raw_plan):
    from eval.runner import oracle_fn
    try:
        block, inv = oracle_fn(raw_plan)
        return {"oracle_block": block, "oracle_invariant": inv}
    except Exception as exc:
        return {"oracle_error": type(exc).__name__}


def run() -> dict:
    rows = []
    for atk in all_malformed():
        row = {"attack_id": atk.attack_id, "goal": atk.goal, "note": atk.note}
        try:
            v = decide(atk.raw_plan)
            row.update(typed=v.decision.value, reason=v.reason,
                       detail=(v.detail or "")[:160], certificate=v.certificate is not None)
        except Exception as exc:
            row.update(typed="CRASH", reason=type(exc).__name__, detail="", certificate=False)
        try:
            row["classifier"] = "BLOCK" if clf_predict(atk.raw_plan)["harmful"] else "PASS"
        except Exception as exc:
            row["classifier"] = f"ERROR:{type(exc).__name__}"
        row["boundary_ok"] = parse_plan(atk.raw_plan).ok
        row.update(_oracle(atk.raw_plan))
        rows.append(row)
    n = len(rows)
    summary = {
        "n": n,
        "typed_pass": sum(r["typed"] == "PASS" for r in rows),
        "typed_block": sum(r["typed"] == "BLOCK" for r in rows),
        "typed_abstain": sum(r["typed"] == "ABSTAIN" for r in rows),
        "typed_crash": sum(r["typed"] == "CRASH" for r in rows),
        "note": "post-registration probe suite; not part of the preregistered held-out "
                "metrics; deterministic arms only (typed gate, classifier, oracle)",
    }
    return {"summary": summary, "rows": rows}


def main() -> int:
    res = run()
    OUT.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    s = res["summary"]
    print(f"probe_malformed: n={s['n']} PASS={s['typed_pass']} BLOCK={s['typed_block']} "
          f"ABSTAIN={s['typed_abstain']} CRASH={s['typed_crash']} -> {OUT.relative_to(REPO)}")
    return 1 if (s["typed_pass"] or s["typed_crash"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
