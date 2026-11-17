# Changelog

All notable changes to lab-gate. Versions follow [Semantic Versioning](https://semver.org/).

## [1.0.0] - unreleased

First packaged release. `pip install lab-gate` gives the gate core as a command and a
small Python API. The decision logic, the seed rules and every published evaluation
number are unchanged from the evaluated version (rule-set hash
`ef9db6e32bd6b4e3e7802ebfae966d9d06b717e21cf9eb948ac3db5c7a95b818`).

### Added
- `lab-gate` command:
  - `lab-gate check PLAN.json [--rules RULES.yaml] [--json] [--horizon K]` prints the
    verdict (PASS with its proof certificate, BLOCK with its counterexample, or
    ABSTAIN with its reason) and the rule-set hash. Exit codes: 0 PASS, 1 BLOCK,
    2 ABSTAIN, 64 usage or input error.
  - `lab-gate examples [DIR]` writes the seed rules and example plans.
  - `lab-gate fetch-data` downloads the OER dataset from helao-async at the pinned
    commit and checks its SHA-256 (needed only for plans with composition steps).
  - `lab-gate version`.
- Python API: `from lab_gate import load_rules, check`. `check(plan, rules)` returns a
  `CheckResult` with `verdict`, `reason`, `certificate`, `counterexample`, `detail`,
  `rule_set_hash`, `plan_hash`, `horizon_k`, `exit_code` and `to_dict()`. It wraps the
  existing `gate.verdict.decide`; the internal modules keep their names.
- `load_rules` refuses a rule that names an action, variable, quantity or element the
  checker does not know, because such a rule would silently never fire.
- `examples/` (seed rules plus plans that pass, block and abstain), `docs/RULES.md`
  (how to write a rule), `docs/RELEASE.md` (release checklist), and a manually
  triggered PyPI publishing workflow.
- Package metadata for PyPI (MIT, Python 3.12+, minimal runtime dependencies). The
  evaluation-only dependencies moved to the `eval` extra.

### Changed
- `gate.verdict.decide` now delegates to `decide_with_registry` (same logic, so the
  API can pass a user-loaded rule set). Verdicts are identical.
- The fitted potential surrogate ships inside the package (`sim_ext/surrogate.json`,
  byte-identical to `results/surrogate.json`), so an installed gate needs no repo
  `results/` folder.
- The OER dataset is also looked for in the per-user cache that `lab-gate
  fetch-data` writes, after `HELAO_DATASET` and `$WS/helao-async`. It is still not
  redistributed with lab-gate.
- Version 0.1.0 -> 1.0.0 (new receipts record `gate_version` 1.0.0; committed
  receipts are unchanged).
