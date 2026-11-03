"""Cost-meter reader/reporter (P6.1 companion).

The meter itself lives in eval/llm.py (every call updates logs/cost_meter.json under
a lock). This module just reports it and checks it against the budget cap, for the
final report and for a quick CLI sanity check.
"""

from __future__ import annotations

import json
from pathlib import Path

WS = Path(__file__).resolve().parent.parent.parent
METER = WS / "logs" / "cost_meter.json"
BUDGET = Path(__file__).resolve().parent.parent / "config" / "budget.yaml"


def report() -> dict:
    meter = json.loads(METER.read_text()) if METER.exists() else {"total_usd": 0.0, "calls": 0, "by_role": {}}
    import yaml
    cap = yaml.safe_load(BUDGET.read_text()).get("hard_cap_usd", 500) if BUDGET.exists() else 500
    meter["hard_cap_usd"] = cap
    meter["within_cap"] = meter["total_usd"] <= cap
    return meter


if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
