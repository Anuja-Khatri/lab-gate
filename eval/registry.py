"""Results registry (P8.4; pattern from refs pipeline/registry.py).

Every headline number is written here, never hand-typed into a doc. Docs and the
site render from this file under the numbers lock (eval/numbers_lock.py). Metric
schema per entry: metric_id, value, ci_lo, ci_hi, n, task, caveats.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO / "results" / "registry.json"


class Registry:
    def __init__(self, path: Path = REGISTRY_PATH):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = {"schema_version": "1.0", "numbers_lock": None, "metrics": []}
        self.data.setdefault("metrics", [])

    def get(self, metric_id: str):
        for m in self.data["metrics"]:
            if m["metric_id"] == metric_id:
                return m
        return None

    def upsert(self, *, metric_id: str, value, n: Optional[int] = None,
               ci_lo: Optional[float] = None, ci_hi: Optional[float] = None,
               task: str = "", caveats: Optional[list] = None):
        entry = {"metric_id": metric_id, "value": value, "ci_lo": ci_lo,
                 "ci_hi": ci_hi, "n": n, "task": task, "caveats": caveats or []}
        for i, m in enumerate(self.data["metrics"]):
            if m["metric_id"] == metric_id:
                self.data["metrics"][i] = entry
                return entry
        self.data["metrics"].append(entry)
        return entry

    def values(self) -> dict:
        return {m["metric_id"]: m["value"] for m in self.data["metrics"]}

    def save(self):
        self.data["metrics"].sort(key=lambda m: m["metric_id"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n")
