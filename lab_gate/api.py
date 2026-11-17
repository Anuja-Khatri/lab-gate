"""Public Python API for lab-gate (stable across 1.x).

This module is a thin wrapper. The decision is made by ``gate.verdict.decide`` /
``gate.verdict.decide_with_registry`` exactly as in the evaluation; nothing here
changes a verdict. It adds: loading a rule file, accepting a plan as a dict or a JSON
file, and a flat result object with the rule-set hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from gate.registry.lock import DEFAULT_REGISTRY, registry_hash
from gate.registry.schema import Registry, load_registry
from gate.verdict import Verdict, _load_config, decide, decide_with_registry

# Exit codes of `lab-gate check` (also exposed as CheckResult.exit_code).
EXIT_PASS = 0
EXIT_BLOCK = 1
EXIT_ABSTAIN = 2
EXIT_USAGE = 64   # bad arguments, unreadable plan or rules file (BSD EX_USAGE)

_EXIT_BY_VERDICT = {"PASS": EXIT_PASS, "BLOCK": EXIT_BLOCK, "ABSTAIN": EXIT_ABSTAIN}

PathLike = Union[str, "os.PathLike[str]"]


@dataclass(frozen=True)
class RuleSet:
    """A validated rule set (the invariant registry) and its SHA-256 hash."""
    registry: Registry
    hash: str
    path: Optional[Path] = None

    @property
    def version(self) -> str:
        return self.registry.version

    @property
    def rule_ids(self) -> list[str]:
        return [inv.id for inv in self.registry.invariants]


@dataclass(frozen=True)
class CheckResult:
    """The outcome of checking one plan against one rule set."""
    verdict: str                      # "PASS" | "BLOCK" | "ABSTAIN"
    reason: str
    rule_set_hash: str
    rule_set_version: str
    plan_hash: str
    horizon_k: int
    certificate: Optional[dict] = None    # PASS proof certificate / BLOCK trace
    counterexample: Optional[list] = None  # BLOCK only: steps up to the violation
    detail: Optional[str] = None           # violated rule id, or abstain detail

    @property
    def ok(self) -> bool:
        """True only for PASS. Anything else means: do not run the plan as is."""
        return self.verdict == "PASS"

    @property
    def exit_code(self) -> int:
        return _EXIT_BY_VERDICT[self.verdict]

    @property
    def violated_rule(self) -> Optional[str]:
        return self.detail if self.verdict == "BLOCK" else None

    def to_dict(self) -> dict:
        from gate import __version__
        return {
            "lab_gate_version": __version__,
            "verdict": self.verdict,
            "reason": self.reason,
            "detail": self.detail,
            "rule_set_hash": self.rule_set_hash,
            "rule_set_version": self.rule_set_version,
            "plan_hash": self.plan_hash,
            "horizon_k": self.horizon_k,
            "certificate": self.certificate,
            "counterexample": self.counterexample,
        }


# Vocabulary a rule may refer to. These are exactly the per-step variables the
# reference and SMT checkers compute (gate/checker/reference.py) and the accounting
# quantities they track (sim_ext/accounting.py). A rule naming anything else would
# be silently skipped by the checker, so load_rules refuses it instead.
DERIVED_VARS = frozenset({
    "action", "predicted_erhe_v", "anneal_temp_over_limit", "sample_qc_passed",
    "action_outside_campaign_capability", "partner_element_not_allowed",
})
SCALAR_QUANTITIES = frozenset({
    "instrument_minutes", "acid_volume_ml", "furnace_minutes", "n_measurements",
})
PER_ELEMENT_QUANTITIES = frozenset({"sputter_target_consumed"})


def lint_rules(registry: Registry) -> list[str]:
    """Problems that would make a rule never fire (or always error). Empty = OK."""
    from gate.boundary.schemas import ACTION_SCHEMAS
    from sim_ext.accounting import ELEMENTS

    probs: list[str] = []
    actions = set(ACTION_SCHEMAS)
    elements = set(ELEMENTS)

    def var_ok(where: str, var: str) -> None:
        if var not in DERIVED_VARS:
            probs.append(f"{where}: unknown variable {var!r} (known: {sorted(DERIVED_VARS)})")

    def action_ok(where: str, name: str) -> None:
        if name not in actions:
            probs.append(f"{where}: unknown action {name!r} (known: {sorted(actions)})")

    for cls, acts in registry.campaign_classes.items():
        for a in acts:
            action_ok(f"campaign_classes.{cls}", a)
    for el in registry.partner_element_allowlist:
        if el not in elements:
            probs.append(f"partner_element_allowlist: unknown element {el!r}")

    for inv in registry.invariants:
        spec = inv.typed_spec()
        kind = str(inv.kind)
        where = f"rule {inv.id}"
        if kind == "bound":
            action_ok(where, spec.action)
            var_ok(where, spec.predicate.var)
        elif kind == "reach":
            if spec.banned is not None:
                var_ok(where, spec.banned.var)
            else:
                action_ok(where, spec.precedence_action)
                var_ok(where, spec.precedence_requires.var)
        elif kind == "forbid_combo":
            for pair in spec.forbidden_pairs:
                for el in pair:
                    if el not in elements:
                        probs.append(f"{where}: unknown element {el!r}")
        elif kind == "accumulate":
            if spec.per == "requester":
                continue  # uses per-requester instrument minutes
            if spec.per == "element":
                if spec.quantity not in PER_ELEMENT_QUANTITIES:
                    probs.append(f"{where}: per: element needs quantity in "
                                 f"{sorted(PER_ELEMENT_QUANTITIES)}, got {spec.quantity!r}")
            elif spec.quantity not in SCALAR_QUANTITIES:
                probs.append(f"{where}: unknown quantity {spec.quantity!r} (known: "
                             f"{sorted(SCALAR_QUANTITIES)}; per-element: "
                             f"{sorted(PER_ELEMENT_QUANTITIES)} with per: element)")
    return probs


def load_rules(path: Optional[PathLike] = None) -> RuleSet:
    """Load and validate a rule file (YAML). With no path, load the bundled seed
    rules (the same file the published evaluation used).

    Raises ``FileNotFoundError`` if the file is missing and ``ValueError`` (pydantic
    ``ValidationError`` is a subclass) if it is not a valid rule set, including a
    rule that names an action, variable, quantity or element the checker does not
    know (such a rule would otherwise silently never fire).
    """
    p = Path(path) if path is not None else DEFAULT_REGISTRY
    if not p.exists():
        raise FileNotFoundError(f"rules file not found: {p}")
    import yaml
    try:
        reg = load_registry(p)
    except yaml.YAMLError as exc:
        raise ValueError(f"rules file is not valid YAML: {p}: {exc}") from None
    problems = lint_rules(reg)
    if problems:
        raise ValueError(f"invalid rules file {p}:\n  " + "\n  ".join(problems))
    return RuleSet(registry=reg, hash=registry_hash(reg), path=p)


def _load_plan(plan: Union[dict, PathLike]) -> dict:
    if isinstance(plan, dict):
        return plan
    p = Path(plan)
    if not p.exists():
        raise FileNotFoundError(f"plan file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"plan file is not valid JSON: {p}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"plan must be a JSON object, got {type(data).__name__}: {p}")
    return data


def check(plan: Union[dict, PathLike], rules: Union[RuleSet, PathLike, None] = None,
          horizon_k: Optional[int] = None) -> CheckResult:
    """Check one plan against a rule set and return a :class:`CheckResult`.

    ``plan``: a plan dict, or the path of a JSON file holding one.
    ``rules``: a :class:`RuleSet` from :func:`load_rules`, a path to a rule file, or
    None for the bundled seed rules. ``horizon_k``: maximum plan length the proof
    covers (default 64); longer plans ABSTAIN.
    """
    raw = _load_plan(plan)
    _, default_hash, default_k = _load_config()
    k = horizon_k if horizon_k is not None else default_k

    if rules is None:
        rs = None
        v: Verdict = decide(raw, horizon_k=horizon_k)
        version = _load_config()[0].version
        rhash = default_hash
    else:
        rs = rules if isinstance(rules, RuleSet) else load_rules(rules)
        v = decide_with_registry(raw, rs.registry, rs.hash, k)
        version = rs.version
        rhash = rs.hash

    return CheckResult(
        verdict=v.decision.value,
        reason=v.reason,
        rule_set_hash=v.registry_hash or rhash,
        rule_set_version=version,
        plan_hash=v.plan_hash,
        horizon_k=k,
        certificate=v.certificate,
        counterexample=v.counterexample,
        detail=v.detail,
    )


# --- the OER dataset (needed for any plan step that carries a composition) -------
def dataset_path() -> Optional[Path]:
    """The OER dataset file the gate will read, or None if none is found.

    Rules about a measurement's predicted potential (I1 in the seed rules) look up
    the measured potential of already-characterised compositions in helao-async's
    ``oer13_cps`` dataset. lab-gate does not redistribute that file; get it with
    ``lab-gate fetch-data`` or point ``HELAO_DATASET`` at a copy.
    """
    from sim_ext.oersim import WS_DATASET, user_cache_dataset

    env = os.environ.get("HELAO_DATASET")
    if env:
        return Path(env) if Path(env).exists() else None
    for p in (WS_DATASET, user_cache_dataset()):
        if p.exists():
            return p
    return None


def fetch_data(dest: Optional[PathLike] = None, url: Optional[str] = None) -> Path:
    """Download the OER dataset from helao-async at the pinned commit, verify its
    SHA-256, and store it in the per-user cache (or ``dest``). Returns the path.

    Also sets ``HELAO_DATASET`` for the current process if it is unset, so a
    following :func:`check` in the same process uses the file.
    """
    from sim_ext.oersim import DATASET_SHA256, DATASET_URL, user_cache_dataset

    target = Path(dest) if dest is not None else user_cache_dataset()
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url or DATASET_URL, timeout=60) as resp:  # noqa: S310
        payload = resp.read()
    got = hashlib.sha256(payload).hexdigest()
    if got != DATASET_SHA256:
        raise ValueError(f"downloaded dataset sha256 {got} != expected {DATASET_SHA256}")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        tmp.write(payload)
    os.chmod(tmp.name, 0o644)
    os.replace(tmp.name, target)
    os.environ.setdefault("HELAO_DATASET", str(target))
    return target


def _plan_needs_dataset(raw: Any) -> bool:
    """True if any action carries a composition (the I1 lookup reads the dataset)."""
    if not isinstance(raw, dict) or not isinstance(raw.get("actions"), list):
        return False
    for a in raw["actions"]:
        if isinstance(a, dict) and isinstance(a.get("action_params"), dict) \
                and "comp_vec" in a["action_params"]:
            return True
    return False
