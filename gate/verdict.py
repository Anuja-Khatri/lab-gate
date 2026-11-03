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


_REGISTRY = None
_REGISTRY_HASH = None
_HORIZON_K = None


def _load_config():
    global _REGISTRY, _REGISTRY_HASH, _HORIZON_K
    if _REGISTRY is None:
        import yaml

        from gate.registry.lock import DEFAULT_REGISTRY, load_registry, registry_hash
        _REGISTRY = load_registry(DEFAULT_REGISTRY)
        _REGISTRY_HASH = registry_hash(_REGISTRY)
        cfg_path = DEFAULT_REGISTRY.parent.parent.parent / "config" / "experiment.yaml"
        try:
            cfg = yaml.safe_load(cfg_path.read_text())
            _HORIZON_K = int(cfg["checker"]["horizon_k"])
        except Exception:
            _HORIZON_K = 64
    return _REGISTRY, _REGISTRY_HASH, _HORIZON_K


def decide(raw_plan: dict, horizon_k: Optional[int] = None) -> Verdict:
    """Top-level decision (P4.3): typed boundary, then reference + SMT checkers.

    - ABSTAIN if the boundary cannot type the plan, or either checker abstains
      (unknown class/substrate, beyond horizon, solver timeout).
    - BLOCK if a violation is found; the counterexample is the violating step
      sequence and the certificate is the BLOCK trace.
    - PASS only if the SMT proves no violation reachable within the horizon AND the
      reference agrees. If reference and SMT disagree, ABSTAIN with reason
      'reference_smt_disagree' (a bug; the equivalence suite P4.5 fails on it).
    """
    from gate.checker.certificates import block_certificate, pass_certificate
    from gate.checker.reference import evaluate
    from gate.checker.smt import encode_and_check

    registry, reg_hash, cfg_k = _load_config()
    k = horizon_k if horizon_k is not None else cfg_k

    parsed, bverdict = boundary_decision(raw_plan)
    ph = bverdict.plan_hash
    bverdict.registry_hash = reg_hash
    if not parsed.ok:
        return bverdict  # ABSTAIN with boundary reason

    ref = evaluate(parsed, registry, horizon_k=k)
    smt = encode_and_check(parsed, registry, horizon_k=k)

    # agreement on the decision and (for BLOCK) the invariant
    same = (ref.decision == smt.decision and ref.invariant_id == smt.invariant_id)
    if not same:
        return Verdict(Decision.ABSTAIN, "reference_smt_disagree", ph, reg_hash,
                       quarantined_text=parsed.quarantined_text,
                       detail=f"ref={ref.decision}/{ref.invariant_id} "
                              f"smt={smt.decision}/{smt.invariant_id}")

    if ref.decision == "BLOCK":
        cert = block_certificate(ph, reg_hash, k, smt.invariant_id,
                                 smt.step_index, smt.counterexample)
        return Verdict(Decision.BLOCK, ref.reason, ph, reg_hash,
                       counterexample=smt.counterexample, certificate=cert,
                       quarantined_text=parsed.quarantined_text,
                       detail=smt.invariant_id)
    if ref.decision == "ABSTAIN":
        return Verdict(Decision.ABSTAIN, smt.reason or ref.reason, ph, reg_hash,
                       quarantined_text=parsed.quarantined_text,
                       detail=smt.invariant_id or ref.invariant_id)
    # PASS
    cert = pass_certificate(ph, reg_hash, k, smt)
    return Verdict(Decision.PASS, "no violation reachable within horizon; "
                   "reference and SMT agree", ph, reg_hash, certificate=cert,
                   quarantined_text=parsed.quarantined_text)


def decide_merged(raw_plans: list[dict], horizon_k: Optional[int] = None) -> Verdict:
    """Shared-lab decision over several requesters' plans (I7, P7.3b)."""
    from gate.checker.reference import evaluate_merged
    registry, reg_hash, _ = _load_config()
    parsed = [parse_plan(rp) for rp in raw_plans]
    res = evaluate_merged(parsed, registry)
    ph = plan_hash(parsed[0]) if parsed else ""
    if res.decision == "BLOCK":
        return Verdict(Decision.BLOCK, res.reason, ph, reg_hash,
                       counterexample=res.counterexample, detail=res.invariant_id)
    return Verdict(Decision.PASS if res.decision == "PASS" else Decision.ABSTAIN,
                   res.reason, ph, reg_hash)
