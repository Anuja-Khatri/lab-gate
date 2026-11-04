"""EXTENSION (not preregistered): scale the LLM adaptive attacker vs the TYPED gate.

Owner extension declared before execution (D-033). Scope is the typed gate ONLY
(typed is not an LLM, so there is no same-vendor issue). The preregistered arm was
6 goals x 2 seeds = n=12, gray-box only (attack.llm_attacker_vs_typed, kept as-is).
This adds seeds and goals to reach n >= 48 trajectories in BOTH modes:

  - black-box: attacker sees only the gate verdict (PASS/BLOCK/ABSTAIN).
  - gray-box:  attacker additionally sees the blocked invariant id on a BLOCK.

8 goals x 6 seeds = 48 trajectories per mode. The typed gate always returns a decided
verdict (no LLM, no ERROR), so n == completed trajectories exactly. Every outcome is
appended to a resumable JSONL ledger, so if the promo headroom / monthly cap interrupts
the run (BudgetExceeded) the completed n is kept and reported, labelled EXTENSION. No
backfill. Attacker model is the preregistered Anthropic claude-opus-5-5; calls are
cached/metered under the adaptive_attacker per-role cap (R-08).
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval import llm
from eval.metrics import rate_ci
from eval.redteam import adaptive
from eval.registry import Registry
from eval.runner import oracle_fn
from gate.verdict import decide

REPO = Path(__file__).resolve().parent.parent
LOGDIR = REPO.parent / "logs"
LEDGER = LOGDIR / "ext_attacker_typed_ledger.jsonl"
ATTACKER_MODEL = "claude-opus-5-5"   # preregistered R-13 attacker model
EXT_GOALS = ["I1", "I2", "I3", "I4", "I5", "I6", "I8", "injection"]   # 8 goals
EXT_SEEDS = [0, 1, 2, 3, 4, 5]                                        # 6 seeds -> 48/mode
EXT_MODES = ["black_box", "gray_box"]
ATK_BUDGET = 20
WORKERS = 16
LABEL = "EXTENSION, not preregistered (D-033)"
_LEDGER_LOCK = threading.Lock()


def typed_fn(p):
    v = decide(p)
    return (v.decision.value, {"blocked_invariant": v.detail or ""})


typed_fn.__name__ = "typed"


def _load_ledger() -> dict:
    done = {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            done[(r["mode"], r["goal"], r["seed"])] = r
    return done


def _append(rec: dict) -> None:
    with _LEDGER_LOCK:
        with LEDGER.open("a") as f:
            f.write(json.dumps(rec) + "\n")


def run(reg: Registry) -> dict:
    LOGDIR.mkdir(parents=True, exist_ok=True)
    done = _load_ledger()
    todo = [(mode, g, s) for mode in EXT_MODES for g in EXT_GOALS for s in EXT_SEEDS
            if (mode, g, s) not in done]
    interrupted = {"hit": False}

    def _one(key):
        mode, g, s = key
        if interrupted["hit"]:
            return
        try:
            r = adaptive.llm_attack(g, typed_fn, oracle_fn, s,
                                    budget=ATK_BUDGET, mode=mode,
                                    model=ATTACKER_MODEL)
        except llm.BudgetExceeded as e:
            if not interrupted["hit"]:
                print(json.dumps({"stopped": "BudgetExceeded", "detail": str(e),
                                  "at": {"mode": mode, "goal": g, "seed": s}}))
            interrupted["hit"] = True
            return
        any_dec = any(a.decision in ("PASS", "BLOCK", "ABSTAIN", "INVALID_JSON")
                      for a in r.trajectory)
        _append({"mode": mode, "goal": g, "seed": s,
                 "success": bool(r.success), "decided": bool(any_dec),
                 "queries": len(r.trajectory)})

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(_one, todo))

    # recompute metrics from the ledger (partial-safe)
    done = _load_ledger()
    out = {}
    for mode in EXT_MODES:
        recs = [r for (m, _g, _s), r in done.items() if m == mode and r["decided"]]
        n = len(recs)
        succ = sum(1 for r in recs if r["success"])
        key = "blackbox" if mode == "black_box" else "graybox"
        complete = n >= 48
        cav = [f"{LABEL}; attacker vs the TYPED gate only (typed is not an LLM, no "
               f"same-vendor issue); {ATTACKER_MODEL} attacker, up to "
               f"{len(EXT_GOALS)} goals x {len(EXT_SEEDS)} seeds x {ATK_BUDGET} queries, "
               f"{mode.replace('_', '-')}; typed gate always decides so n == completed "
               f"trajectories"]
        if not complete:
            cav.append(f"PARTIAL: cap/headroom interrupted the run; completed n={n} kept, "
                       "not backfilled")
        reg.upsert(metric_id=f"attack.llm_attacker_vs_typed.{key}_ext", task="P8-ext",
                   caveats=cav, **rate_ci(succ, n))
        out[key] = {"n": n, "success": succ, "complete": complete}
    reg.save()

    meter = json.loads((LOGDIR / "cost_meter.json").read_text())
    reg.upsert(metric_id="llm.spend_usd", value=round(meter["total_usd"], 4),
               n=meter["calls"], task="P8",
               caveats=["cumulative metered LLM spend across all runs (cap 500)"])
    reg.save()
    out["spend_usd"] = meter["total_usd"]
    out["interrupted"] = interrupted["hit"]
    return out


def main() -> int:
    print(json.dumps(run(Registry())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
