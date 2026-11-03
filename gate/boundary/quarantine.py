"""Free-text quarantine (P2.3).

No decision path may read any free-text field. Before a plan is parsed into typed
schemas, every free-text field is stripped and set aside. The stripped text is
stored ONLY in the receipt (gate/receipts.py); it is never passed to the checker
(gate/checker/) or the verdict logic (gate/verdict.py). A static check
(tests/test_no_text_channel.py) asserts those modules never even name these fields.

Field names and their source models in helao-async (see docs/P0_MEMO.md Section 5):
  action_comment       core/models/action.py:57
  experiment_comment   core/models/experiment.py:51
  experiment_label     core/models/experiment.py:114
  sequence_comment     core/models/sequence.py:48
  sequence_label       core/models/sequence.py:47
"""

from __future__ import annotations

from typing import Any

# Every free-text field name that must never reach a decision path.
FREE_TEXT_FIELDS: frozenset[str] = frozenset({
    "action_comment",
    "experiment_comment",
    "experiment_label",
    "sequence_comment",
    "sequence_label",
})


def _strip_mapping(d: dict, collected: dict, path: str) -> dict:
    """Return a copy of ``d`` with FREE_TEXT_FIELDS removed, recursively, and
    record removed values into ``collected`` keyed by a dotted path."""
    clean: dict[str, Any] = {}
    for k, v in d.items():
        if k in FREE_TEXT_FIELDS:
            collected[f"{path}{k}"] = v
            continue
        if isinstance(v, dict):
            clean[k] = _strip_mapping(v, collected, f"{path}{k}.")
        elif isinstance(v, list):
            clean[k] = [
                _strip_mapping(item, collected, f"{path}{k}[{i}].")
                if isinstance(item, dict) else item
                for i, item in enumerate(v)
            ]
        else:
            clean[k] = v
    return clean


def quarantine_plan(raw_plan: dict) -> tuple[dict, dict]:
    """Split a raw plan into (clean_plan, quarantined_text).

    ``clean_plan`` is a deep copy with every free-text field removed at any depth
    (plan level, per-action level, and nested). ``quarantined_text`` maps a dotted
    path to the removed value, for the receipt only.

    The clean plan is what every downstream component is allowed to see.
    """
    if not isinstance(raw_plan, dict):
        raise TypeError(f"plan must be a dict, got {type(raw_plan).__name__}")
    collected: dict[str, Any] = {}
    clean = _strip_mapping(raw_plan, collected, "")
    return clean, collected
