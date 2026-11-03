"""Verdict types and the decision entrypoint.

The gate returns exactly one of PASS / BLOCK / ABSTAIN. This module owns the
verdict datatype and the boundary stage of the decision. The checker stages
(reference + SMT) are wired in Phase 4 via ``decide``; until then ``decide`` runs
the typed boundary and returns ABSTAIN for anything it cannot certify as typeable,
and a provisional TYPED_OK marker for well-typed plans (never PASS without a
proof). No decision path reads any free-text field: the only text a verdict
carries is in ``quarantined_text``, which is copied to the receipt and never read
by the checker.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from gate.boundary.schemas import ParsedPlan, parse_plan


class Decision(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    ABSTAIN = "ABSTAIN"
    # provisional marker used only before the Phase 4 checker is wired; never a
    # final verdict in a built gate.
    TYPED_OK = "TYPED_OK"


@dataclass
class Verdict:
    decision: Decision
    reason: str
    plan_hash: str
    registry_hash: Optional[str] = None
    certificate: Optional[dict] = None       # PASS proof (Phase 4)
    counterexample: Optional[list] = None     # BLOCK trace (Phase 4)
    quarantined_text: dict = field(default_factory=dict)
    detail: Optional[str] = None

    def to_public(self) -> dict:
        """Verdict view that NEVER includes quarantined text (for checker I/O)."""
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "plan_hash": self.plan_hash,
            "registry_hash": self.registry_hash,
            "certificate": self.certificate,
            "counterexample": self.counterexample,
            "detail": self.detail,
        }


def plan_fingerprint(parsed: ParsedPlan) -> str:
    """Canonical serialisation of the TYPED plan (no free text) for hashing and
    byte-identity assertions. Depends only on quarantined content."""
    payload = {
        "provenance": {
            "requester_id": parsed.provenance.requester_id,
            "requester_class": parsed.provenance.requester_class,
            "campaign_name": parsed.provenance.campaign_name,
            "campaign_class": parsed.provenance.campaign_class,
            "window_id": parsed.provenance.window_id,
        },
        "ok": parsed.ok,
        "abstain_reason": parsed.abstain_reason,
        "actions": [
            {
                "index": a.index,
                "server": a.server,
                "action_name": a.action_name,
                "is_native": a.is_native,
                "params": a.params.model_dump(mode="json"),
            }
            for a in parsed.actions
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def plan_hash(parsed: ParsedPlan) -> str:
    return hashlib.sha256(plan_fingerprint(parsed).encode("utf-8")).hexdigest()


def boundary_decision(raw_plan: dict) -> tuple[ParsedPlan, Verdict]:
    """Run the typed boundary and produce a boundary-stage verdict.

    Returns (parsed, verdict). If the boundary could not type the plan, the verdict
    is ABSTAIN with the boundary's reason. If the plan is well typed, the verdict is
    the provisional TYPED_OK marker (Phase 4 replaces this branch with the checker).
    The verdict depends ONLY on the quarantined (free-text-stripped) plan.
    """
    parsed = parse_plan(raw_plan)
    ph = plan_hash(parsed)
    if not parsed.ok:
        return parsed, Verdict(
            decision=Decision.ABSTAIN,
            reason=parsed.abstain_reason or "unparseable",
            plan_hash=ph,
            quarantined_text=parsed.quarantined_text,
            detail=parsed.detail,
        )
    return parsed, Verdict(
        decision=Decision.TYPED_OK,
        reason="typed; checker wired in Phase 4",
        plan_hash=ph,
        quarantined_text=parsed.quarantined_text,
    )


def decide(raw_plan: dict) -> Verdict:
    """Top-level decision. Phase 2: boundary only. Phase 4 adds reference+SMT."""
    _, verdict = boundary_decision(raw_plan)
    return verdict
