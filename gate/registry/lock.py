"""Registry lock (P3.3): canonical serialisation and SHA-256.

Every verdict and every reported result records the registry hash, so a result is
always attributable to an exact policy. The hash is over a canonical JSON of the
loaded, normalised registry (including the generated ltlf/pattern fields), so it is
stable across runs and independent of YAML key order or formatting.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from gate.registry.schema import Registry, load_registry

DEFAULT_REGISTRY = Path(__file__).resolve().parent / "invariants.yaml"


def canonical_registry_dict(reg: Registry) -> dict:
    """A deterministic, JSON-serialisable view of the registry."""
    return {
        "version": reg.version,
        "composition_sum": reg.composition_sum,
        "campaign_classes": {k: sorted(v) for k, v in sorted(reg.campaign_classes.items())},
        "partner_element_allowlist": sorted(reg.partner_element_allowlist),
        "invariants": [
            {
                "id": inv.id,
                "kind": str(inv.kind),
                "scope": str(inv.scope),
                "plain_english": " ".join(inv.plain_english.split()),
                "rationale": " ".join(inv.rationale.split()),
                "source": " ".join(inv.source.split()),
                "spec": inv.spec,
                "extra": inv.extra,
                "pattern": inv.pattern,
                "ltlf": inv.ltlf,
            }
            for inv in sorted(reg.invariants, key=lambda i: i.id)
        ],
    }


def canonical_json(reg: Registry) -> str:
    return json.dumps(canonical_registry_dict(reg), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)


def registry_hash(reg: Registry) -> str:
    return hashlib.sha256(canonical_json(reg).encode("utf-8")).hexdigest()


def load_and_hash(path: Optional[Path] = None) -> tuple[Registry, str]:
    reg = load_registry(path or DEFAULT_REGISTRY)
    return reg, registry_hash(reg)


if __name__ == "__main__":
    reg, h = load_and_hash()
    print(f"registry {reg.version}: {len(reg.invariants)} invariants, sha256 {h[:16]}...")
