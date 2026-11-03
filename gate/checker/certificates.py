"""Verdict certificates (P4.4).

A PASS certificate records enough to re-check the decision: the registry hash, the
plan hash, the horizon, the per-invariant SMT result (UNSAT = no violation
reachable), the Z3 version, and the bounded/unbounded status per invariant. A BLOCK
certificate is the concrete counterexample: the violating step index and the full
prefix of the abstract state trace up to and including it.

Certificates never contain free text (the quarantined comments live only in the
receipt, gate/receipts.py).
"""

from __future__ import annotations

from typing import Optional

from gate.checker.smt import SmtResult


def pass_certificate(plan_hash: str, registry_hash: str, horizon_k: int,
                     smt: SmtResult) -> dict:
    cert = dict(smt.certificate or {})
    cert.update({
        "kind": "PASS",
        "plan_hash": plan_hash,
        "registry_hash": registry_hash,
        "horizon_k": horizon_k,
    })
    return cert


def block_certificate(plan_hash: str, registry_hash: str, horizon_k: int,
                      invariant_id: Optional[str], step_index: Optional[int],
                      counterexample: Optional[list]) -> dict:
    return {
        "kind": "BLOCK",
        "plan_hash": plan_hash,
        "registry_hash": registry_hash,
        "horizon_k": horizon_k,
        "violated_invariant": invariant_id,
        "violating_step": step_index,
        "counterexample": counterexample,
    }
