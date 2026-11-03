"""Orchestrator-dispatch gate hook (P5.2).

The same gate applied at orchestrator dispatch for plans that do NOT originate from
the OERSIM decision step (docs/P0_MEMO.md Section 3: `_stage_action_for_dispatch` /
`_dispatch_action_locked`). A single entry point decides a plan, writes a receipt,
and returns the routing action. A merged entry point gates several requesters'
plans against the shared-lab window invariant (I7, P7.3b).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from gate.receipts import write_receipt
from gate.verdict import Decision, Verdict, decide, decide_merged


def gate_dispatch(raw_plan: dict, receipts_path: Optional[Path] = None) -> tuple[str, Verdict]:
    """Decide one plan at dispatch. Returns (routing, verdict) where routing is
    'proceed' (PASS), 'cancel' (BLOCK) or 'hold' (ABSTAIN -> human queue)."""
    verdict = decide(raw_plan)
    write_receipt(verdict, receipts_path)
    routing = {Decision.PASS: "proceed", Decision.BLOCK: "cancel",
               Decision.ABSTAIN: "hold"}.get(verdict.decision, "hold")
    return routing, verdict


def gate_dispatch_merged(raw_plans: list[dict],
                         receipts_path: Optional[Path] = None) -> tuple[str, Verdict]:
    """Gate several requesters' plans against the shared-lab window budget (I7)."""
    verdict = decide_merged(raw_plans)
    write_receipt(verdict, receipts_path)
    routing = {Decision.PASS: "proceed", Decision.BLOCK: "cancel",
               Decision.ABSTAIN: "hold"}.get(verdict.decision, "hold")
    return routing, verdict
