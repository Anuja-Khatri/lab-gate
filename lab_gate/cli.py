"""The `lab-gate` command.

    lab-gate check PLAN.json [--rules RULES.yaml] [--json] [--horizon K]
    lab-gate examples [DIR]      write the seed rules and example plans into DIR
    lab-gate fetch-data          download the OER dataset (helao-async, pinned)
    lab-gate version

Exit codes of `check`: 0 PASS, 1 BLOCK, 2 ABSTAIN, 64 usage or input error.
Anything other than 0 means: do not run the plan as written.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path
from typing import Optional

from lab_gate.api import (
    EXIT_USAGE,
    CheckResult,
    _load_plan,
    _plan_needs_dataset,
    check,
    dataset_path,
    fetch_data,
    load_rules,
)

EXAMPLE_PLANS = ("plan_pass.json", "plan_block.json", "plan_abstain.json")


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error; 2 means ABSTAIN here, so use 64."""

    def error(self, message: str):  # pragma: no cover - exercised via subprocess
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="lab-gate",
                description="Check an experiment plan against written rules before it runs.")
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND", parser_class=_Parser)

    c = sub.add_parser("check", help="check a plan (exit 0 PASS, 1 BLOCK, 2 ABSTAIN, 64 error)")
    c.add_argument("plan", help="plan JSON file")
    c.add_argument("--rules", help="rules YAML file (default: the bundled seed rules)")
    c.add_argument("--json", action="store_true", help="print the full result as JSON")
    c.add_argument("--horizon", type=int, default=None,
                   help="max plan length the proof covers (default 64); longer plans ABSTAIN")

    e = sub.add_parser("examples", help="write the seed rules and example plans into DIR")
    e.add_argument("dir", nargs="?", default=".", help="target directory (default: .)")
    e.add_argument("--force", action="store_true", help="overwrite existing files")

    f = sub.add_parser("fetch-data",
                       help="download the OER dataset from helao-async (pinned, sha256-checked)")
    f.add_argument("--dest", help="where to store it (default: per-user cache)")

    sub.add_parser("version", help="print the lab-gate version")
    return p


def _watched_var(rules, rule_id: Optional[str]) -> Optional[str]:
    """The accounting quantity or derived variable the violated rule looks at."""
    if rules is None or rule_id is None:
        return None
    for inv in rules.registry.invariants:
        if inv.id == rule_id:
            spec = inv.typed_spec()
            if getattr(spec, "quantity", None):
                return spec.quantity
            pred = getattr(spec, "predicate", None) or getattr(spec, "banned", None) \
                or getattr(spec, "precedence_requires", None)
            return pred.var if pred is not None else None
    return None


def _window_rules(rules) -> list[str]:
    if rules is None:
        return []
    return [inv.id for inv in rules.registry.invariants
            if str(inv.kind) == "accumulate" and inv.typed_spec().window is not None]


def _fmt_human(r: CheckResult, rules_label: str, rules=None) -> str:
    out = [f"verdict:   {r.verdict}",
           f"reason:    {r.reason}"]
    if r.detail and r.verdict != "PASS":
        out.append(f"detail:    {r.detail}")
    out.append(f"rule set:  {r.rule_set_version} ({rules_label})")
    out.append(f"rule hash: {r.rule_set_hash}")
    out.append(f"plan hash: {r.plan_hash}")

    if r.verdict == "PASS" and r.certificate:
        c = r.certificate
        out.append("certificate (proof):")
        out.append(f"  solver:   {c.get('solver')} {c.get('z3_version', '')}".rstrip())
        out.append(f"  result:   {c.get('result')}")
        out.append(f"  horizon:  {c.get('horizon_k')} actions")
        window = _window_rules(rules)
        listed = [i for i in c.get("invariants_unsat", []) if i not in window]
        out.append(f"  rules with no reachable violation: {', '.join(listed)}")
        if window:
            out.append(f"  not checked on a single plan: {', '.join(window)} (shared-window "
                       "rules need every requester's plan together)")
        status = c.get("invariant_status") or {}
        if status:
            out.append("  bounded to the horizon only: "
                       + ", ".join(k for k, v in sorted(status.items()) if v == "bounded"))
    elif r.verdict == "BLOCK" and r.counterexample is not None:
        cert = r.certificate or {}
        step = cert.get("violating_step")
        out.append(f"counterexample (rule {r.detail} first violated at step {step}):")
        watched = _watched_var(rules, r.detail)
        for s in r.counterexample:
            d = s.get("derived", {})
            acc = s.get("accounting", {})
            bits = []
            if watched and watched in acc:
                bits.append(f"{watched}={acc[watched]}")
            elif watched and watched in d and watched != "predicted_erhe_v":
                bits.append(f"{watched}={d[watched]}")
            if d.get("elements"):
                bits.append("elements=" + "+".join(d["elements"]))
            if d.get("predicted_erhe_v") is not None:
                bits.append(f"predicted_erhe_v={d['predicted_erhe_v']}")
            mark = "   <- violation" if s.get("index") == step else ""
            out.append(f"  step {s.get('index')}: {s.get('action')} {' '.join(bits)}".rstrip()
                       + mark)
        out.append("  (full accounting state per step: re-run with --json)")
    elif r.verdict == "ABSTAIN":
        out.append("ABSTAIN means the gate could not decide; route the plan to a human.")
    return "\n".join(out)


def _cmd_check(args) -> int:
    try:
        raw = _load_plan(args.plan)
        rules = load_rules(args.rules) if args.rules else None
    except (FileNotFoundError, ValueError) as exc:
        print(f"lab-gate: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.horizon is not None and args.horizon < 1:
        print("lab-gate: error: --horizon must be >= 1", file=sys.stderr)
        return EXIT_USAGE

    if _plan_needs_dataset(raw) and dataset_path() is None:
        print("lab-gate: warning: this plan has composition steps, and rules about them "
              "need the OER dataset, which was not found. The gate will ABSTAIN. "
              "Run `lab-gate fetch-data` once (or set HELAO_DATASET).", file=sys.stderr)

    res = check(raw, rules, horizon_k=args.horizon)
    if args.json:
        print(json.dumps(res.to_dict(), indent=2, sort_keys=True))
    else:
        label = str(args.rules) if args.rules else "bundled seed rules"
        print(_fmt_human(res, label, rules or load_rules()))
    return res.exit_code


def _cmd_examples(args) -> int:
    target = Path(args.dir)
    target.mkdir(parents=True, exist_ok=True)
    files = {"rules.yaml": resources.files("gate.registry").joinpath("invariants.yaml")}
    for name in EXAMPLE_PLANS:
        files[name] = resources.files("lab_gate.examples").joinpath(name)
    existing = [n for n in files if (target / n).exists()]
    if existing and not args.force:
        print(f"lab-gate: error: would overwrite {', '.join(existing)} in {target} "
              "(use --force)", file=sys.stderr)
        return EXIT_USAGE
    for name, src in files.items():
        with resources.as_file(src) as sp:
            shutil.copyfile(sp, target / name)
        print(f"wrote {target / name}")
    return 0


def _cmd_fetch_data(args) -> int:
    try:
        path = fetch_data(dest=args.dest)
    except Exception as exc:  # network, TLS or checksum failure
        print(f"lab-gate: error: could not fetch the dataset: {exc}", file=sys.stderr)
        return 1
    print(f"OER dataset saved to {path} (sha256 verified)")
    if args.dest:
        print(f"set HELAO_DATASET={path} so lab-gate finds it")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return _cmd_check(args)
    if args.cmd == "examples":
        return _cmd_examples(args)
    if args.cmd == "fetch-data":
        return _cmd_fetch_data(args)
    if args.cmd == "version":
        from gate import __version__
        print(f"lab-gate {__version__}")
        return 0
    parser.print_help(sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
