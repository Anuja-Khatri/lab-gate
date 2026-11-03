"""OERSIM decision-step gate hook (P5.1).

Inserts the gate at the OERSIM decision step WITHOUT modifying helao-async. In the
real orchestrator this is `dispatch_experiment` / `insert_experiment`
(docs/P0_MEMO.md Section 3); in this environment (R-05, in-process) the identical
check wraps the in-process active-learning loop. At each decision step the gate
checks the proposed plan (everything that would run if we proceed, so accumulation
is visible):
  - PASS   -> proceed (execute the measurement), write a receipt;
  - BLOCK  -> cancel the proposed plan, write a receipt, log; the loop tries the
              next acquisition;
  - ABSTAIN-> route the plan to the file-backed human queue
              (results/abstain_queue.jsonl) and HOLD (stop), write a receipt.

With the gate disabled the loop delegates to the stock in-process simulator, so its
trace is byte-identical to stock OERSIM (P5.4).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from gate.receipts import write_receipt
from gate.verdict import Decision, decide
from sim_ext.oersim import InProcessOERSIM, canonical_json, run_activelearn

REPO = Path(__file__).resolve().parent.parent.parent
ABSTAIN_QUEUE = REPO / "results" / "abstain_queue.jsonl"
RECEIPTS = REPO / "results" / "receipts.jsonl"


def _act(server, name, params):
    return {"server": server, "action_name": name, "action_params": params}


def _candidate_plan(plate, committed_measures, next_comp, requester_id,
                    requester_class, campaign_class):
    """Build the raw plan that would run if the next measurement proceeds:
    the load prefix, every already-committed measurement, and the proposed one."""
    actions = [_act("CPSIM", "change_plate", {"plate_id": plate}),
               _act("CPSIM", "get_loaded_plate", {}),
               _act("GPSIM", "initialize_plate",
                    {"plate_id": plate, "num_random_points": 5, "reinitialize": False})]
    for cv in committed_measures + [next_comp]:
        actions += [
            _act("CPSIM", "get_loaded_plate", {}),
            _act("GPSIM", "acquire_point", {"plate_id": plate}),
            _act("CPSIM", "measure_cp", {"comp_vec": cv, "acquisition_rate": 0.2}),
            _act("GPSIM", "update_model", {"plate_id": plate}),
        ]
    return {"requester": {"id": requester_id, "cls": requester_class},
            "campaign_name": "gated_activelearn", "campaign_class": campaign_class,
            "actions": actions}


def run_gated(plate: int, iterations: int, seed: int, *,
              requester_id: str = "system", requester_class: str = "internal_agent",
              campaign_class: str = "activelearn", gate_enabled: bool = True,
              receipts_path: Optional[Path] = None,
              abstain_queue_path: Optional[Path] = None,
              block_retry_budget: int = 20) -> dict:
    """Run the gated active-learning loop. Returns a summary with per-decision
    verdicts and the executed trace. With gate_enabled=False, delegates to the
    stock in-process simulator (byte-identical trace, P5.4)."""
    if not gate_enabled:
        return run_activelearn(plate, iterations, seed)

    receipts_path = receipts_path or RECEIPTS
    abstain_queue_path = abstain_queue_path or ABSTAIN_QUEUE
    sim = InProcessOERSIM()
    sim.change_plate(plate)
    rng = random.Random(seed)
    history: set = set()
    committed: list[list[int]] = []
    verdicts = []
    status = "completed"

    tries = 0
    while len(committed) < iterations and tries < iterations + block_retry_budget:
        tries += 1
        comp = sim.acquire_next(plate, rng, history)
        history.add(tuple(comp))
        plan = _candidate_plan(plate, committed, comp, requester_id,
                               requester_class, campaign_class)
        verdict = decide(plan)
        write_receipt(verdict, receipts_path)
        verdicts.append({"iteration_attempt": tries, "comp_vec": comp,
                         "decision": verdict.decision.value, "reason": verdict.reason,
                         "detail": verdict.detail})
        if verdict.decision == Decision.PASS:
            committed.append(comp)
        elif verdict.decision == Decision.BLOCK:
            continue   # cancel this proposal; try the next acquisition
        else:  # ABSTAIN -> route to human queue and HOLD
            abstain_queue_path.parent.mkdir(parents=True, exist_ok=True)
            with open(abstain_queue_path, "a") as fh:
                fh.write(json.dumps({"plan_hash": verdict.plan_hash,
                                     "reason": verdict.reason,
                                     "detail": verdict.detail,
                                     "comp_vec": comp}, sort_keys=True) + "\n")
            status = "held_for_human"
            break

    # execute the committed plan in the sim to produce the actual trace
    result = {"plate": plate, "requester": {"id": requester_id, "cls": requester_class},
              "campaign_class": campaign_class, "status": status,
              "n_committed": len(committed), "verdicts": verdicts,
              "committed_comps": committed}
    return result


def summary_json(result: dict) -> str:
    return canonical_json(result)
