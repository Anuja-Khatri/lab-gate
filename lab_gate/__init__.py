"""lab-gate: check an experiment plan against written rules before it runs.

Stable public API (1.x)::

    from lab_gate import load_rules, check

    rules = load_rules("rules.yaml")      # or load_rules() for the bundled seed rules
    result = check(plan_dict, rules)      # or check("plan.json", rules)
    result.verdict          # "PASS" | "BLOCK" | "ABSTAIN"
    result.reason
    result.certificate      # PASS: proof certificate; BLOCK: the BLOCK trace
    result.counterexample   # BLOCK: violating step sequence; else None
    result.rule_set_hash    # sha256 of the canonical rule set

The decision itself is ``gate.verdict.decide`` (unchanged); this package only wraps
it with a small, stable surface and a command-line tool.
"""

from gate import __version__
from lab_gate.api import (
    EXIT_ABSTAIN,
    EXIT_BLOCK,
    EXIT_PASS,
    EXIT_USAGE,
    CheckResult,
    RuleSet,
    check,
    dataset_path,
    fetch_data,
    lint_rules,
    load_rules,
)

__all__ = [
    "__version__",
    "load_rules",
    "check",
    "CheckResult",
    "RuleSet",
    "dataset_path",
    "fetch_data",
    "lint_rules",
    "EXIT_PASS",
    "EXIT_BLOCK",
    "EXIT_ABSTAIN",
    "EXIT_USAGE",
]
