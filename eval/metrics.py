"""Metrics with confidence intervals (P8.3).

Wilson 95% CI for rates; bootstrap 95% CI for curves. Pure functions over the
held-out records; no randomness except the seeded bootstrap.
"""

from __future__ import annotations

import math
import random


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple:
    """Wilson score interval for a binomial rate k/n. Returns (rate, lo, hi)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (round(p, 6), round(max(0.0, center - half), 6), round(min(1.0, center + half), 6))


def rate_ci(successes: int, n: int) -> dict:
    p, lo, hi = wilson(successes, n)
    return {"value": p, "ci_lo": lo, "ci_hi": hi, "n": n}


# Non-verdicts: a gate call that did not return a usable PASS/BLOCK/ABSTAIN. These are
# scored as REDUCED n (excluded from the denominator), never as a verdict (D-030).
NON_VERDICTS = frozenset({"ERROR", "DEFERRED", "CACHE_MISS", "UNPARSEABLE", ""})


def decided(decisions: list) -> list:
    """Keep only genuine verdicts (PASS/BLOCK/ABSTAIN); drop ERROR/DEFERRED/etc."""
    return [d for d in decisions if d not in NON_VERDICTS]


def rate_over_decided(decisions: list, is_hit) -> dict:
    """Rate of is_hit(d) over DECIDED verdicts only (ERROR excluded from n). Returns
    a rate_ci dict plus n_errors (how many non-verdicts were excluded)."""
    dec = decided(decisions)
    k = sum(1 for d in dec if is_hit(d))
    out = rate_ci(k, len(dec))
    out["n_errors_excluded"] = len(decisions) - len(dec)
    return out


def bootstrap_rate_ci(bools: list, seed: int = 20261103, resamples: int = 1000) -> dict:
    """Bootstrap 95% CI of a mean of 0/1 values (deterministic given seed)."""
    n = len(bools)
    if n == 0:
        return {"value": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "n": 0}
    rng = random.Random(seed)
    base = sum(bools) / n
    means = []
    for _ in range(resamples):
        s = sum(bools[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * resamples)]
    hi = means[int(0.975 * resamples)]
    return {"value": round(base, 6), "ci_lo": round(lo, 6), "ci_hi": round(hi, 6), "n": n}


def success_curve(records: list, gate: str, budgets: list, seed: int = 20261103) -> list:
    """Attack-success rate vs attacker budget for a gate (adaptive records).

    A record counts as success-by-budget B if it succeeded using <= B queries.
    """
    rows = [r for r in records if r.get("suite") == "adaptive" and r["gate"] == gate]
    out = []
    for b in budgets:
        bools = [1 if (r["success"] and r["queries_used"] <= b) else 0 for r in rows]
        ci = bootstrap_rate_ci(bools, seed=seed)
        out.append({"budget": b, **ci})
    return out
