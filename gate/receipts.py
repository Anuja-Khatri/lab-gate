"""Receipts (P5.3).

Every verdict writes one JSONL receipt: timestamp, plan hash, registry hash, gate
version, the verdict (decision + reason), the certificate (PASS) or counterexample
(BLOCK), and the quarantined free text. The quarantined text is STORED here for
auditability but is never read by the checker or the verdict logic (it only ever
flows boundary -> receipt). Receipts are the audit trail a human reviewer reads
(HUMAN_CHECKPOINTS H5).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gate import __version__ as GATE_VERSION
from gate.verdict import Verdict

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RECEIPTS = REPO / "results" / "receipts.jsonl"


def make_receipt(verdict: Verdict, *, timestamp: Optional[str] = None) -> dict:
    """Build a receipt dict from a verdict (deterministic except timestamp)."""
    return {
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "gate_version": GATE_VERSION,
        "plan_hash": verdict.plan_hash,
        "registry_hash": verdict.registry_hash,
        "decision": verdict.decision.value,
        "reason": verdict.reason,
        "detail": verdict.detail,
        "certificate": verdict.certificate,
        "counterexample": verdict.counterexample,
        # stored for audit; never read by the checker (no text channel).
        "quarantined_text": verdict.quarantined_text,
    }


def write_receipt(verdict: Verdict, path: Optional[Path] = None,
                  timestamp: Optional[str] = None) -> dict:
    """Append one receipt line and return it."""
    path = path or DEFAULT_RECEIPTS
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = make_receipt(verdict, timestamp=timestamp)
    with open(path, "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    return rec
