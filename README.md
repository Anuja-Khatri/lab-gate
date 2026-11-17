# lab-gate

Check an autonomous lab's experiment plan against written rules before it runs.
lab-gate returns exactly one of:

- **PASS** with a proof certificate,
- **BLOCK** with a counterexample step sequence,
- **ABSTAIN** with a reason, so a human decides.

No decision path reads any free-text field. lab-gate is built on the public
[`helao-async`](https://github.com/High-Throughput-Experimentation/helao-async)
framework and evaluated inside its OER electrocatalysis simulator (OERSIM). It is an
independent project; it is not a contribution to, or endorsed by, helao-async or any
company.

It is a research tool, tested in simulation only. Read
[What it does NOT do](#what-it-does-not-do) before relying on it.

## Install

```
pip install lab-gate
```

Python 3.12 or newer. The runtime dependencies are pydantic, pint, PyYAML, NumPy,
pyzstd and z3-solver. helao-async itself is not needed (see
[What it needs](#what-it-needs)).

## Quickstart

```
lab-gate examples .                                   # writes rules.yaml + 3 example plans
lab-gate check plan_pass.json    --rules rules.yaml   # PASS,    exit code 0
lab-gate check plan_block.json   --rules rules.yaml   # BLOCK,   exit code 1
lab-gate check plan_abstain.json --rules rules.yaml   # ABSTAIN, exit code 2
lab-gate check plan_block.json   --rules rules.yaml --json   # machine-readable
```

The block example is five anneals. Each is within its substrate's temperature limit;
together they overrun the furnace-time rule. The output names the rule, shows the
step sequence that breaks it, and gives the hash of the rule set it was checked
against:

```
verdict:   BLOCK
reason:    I3b violated: Total furnace occupancy must not exceed 240 minutes per campaign.
detail:    I3b
rule set:  lab-gate-registry-v1 (rules.yaml)
rule hash: ef9db6e32bd6b4e3e7802ebfae966d9d06b717e21cf9eb948ac3db5c7a95b818
plan hash: feb6bdf46dce74ba8d515a6a16230339cea853782892e00ce1429fc1e8a4ef74
counterexample (rule I3b first violated at step 4):
  step 0: anneal furnace_minutes=60.0
  step 1: anneal furnace_minutes=120.0
  step 2: anneal furnace_minutes=180.0
  step 3: anneal furnace_minutes=240.0
  step 4: anneal furnace_minutes=300.0   <- violation
  (full accounting state per step: re-run with --json)
```

The same from Python:

```python
from lab_gate import load_rules, check

rules = load_rules("rules.yaml")          # load_rules() alone = the bundled seed rules
result = check("plan_block.json", rules)  # a plan dict works too

print(result.verdict)                     # BLOCK
print(result.reason)                      # I3b violated: Total furnace occupancy ...
print(result.rule_set_hash)               # ef9db6e32bd6b4e3...
print(result.counterexample[-1]["accounting"]["furnace_minutes"])   # 300.0
print(check("plan_pass.json", rules).certificate["result"])
# UNSAT per invariant (no violation reachable within horizon)
```

`check` returns a `CheckResult` with `verdict`, `reason`, `detail`, `certificate`,
`counterexample`, `rule_set_hash`, `plan_hash`, `horizon_k`, `exit_code`, `ok` and
`to_dict()`. The same example files are in [`examples/`](https://github.com/Anuja-Khatri/lab-gate/tree/main/examples) in this
repository.

## The three verdicts

| verdict | meaning | what you get | exit code |
|---|---|---|---|
| PASS | No rule can be violated by this plan within the horizon (64 actions by default). Two independent checkers (a reference evaluator and the Z3 SMT solver) agree. | A proof certificate: solver, horizon, the rules shown unsatisfiable, and which proofs hold only up to the horizon. | 0 |
| BLOCK | A rule is violated. | The violated rule, and the counterexample: every step up to the violating one with the accounting state at each step. | 1 |
| ABSTAIN | The gate cannot decide: an unknown action, campaign class or substrate, a malformed or out-of-range parameter, a plan longer than the horizon, missing data, or a checker disagreement or error. | The reason. Route the plan to a human. | 2 |

`lab-gate check` exits with 64 on a usage or input error (bad arguments, an
unreadable plan, an invalid rule file). **Anything other than 0 means: do not run the
plan as written.** `lab-gate version` prints the version.

## Writing rules

A rule set is a YAML file. A rule has an id, a kind, a plain-English statement, a
rationale, a source, and a strict spec. There are four kinds: `bound` (a limit on one
action), `reach` (a state that must never be reached, or an action that must come
after another), `forbid_combo` (elements that may not appear together), and
`accumulate` (a running total that must stay under a limit). For example:

```yaml
  - id: R1
    kind: accumulate
    plain_english: Total instrument time must not exceed 120 minutes per campaign.
    scope: any
    rationale: Why this rule exists.
    source: Where the limit comes from.
    spec: {quantity: instrument_minutes, agg: sum, limit: 120}
```

Rules are written over a fixed vocabulary of action types, per-step variables and
accumulated quantities; lab-gate is not a general rule engine. `load_rules` refuses a
rule that names something the checker does not know, because such a rule would
otherwise never fire. The full specification, including the plan format, is in
[`docs/RULES.md`](https://github.com/Anuja-Khatri/lab-gate/blob/main/docs/RULES.md). The seed rules in
[`examples/rules.yaml`](https://github.com/Anuja-Khatri/lab-gate/blob/main/examples/rules.yaml) are a complete, commented example.

## What it needs

- **Plans without composition steps** (like the three examples above) need only
  `pip install lab-gate`.
- **Plans with composition steps** (`measure_cp`, `durability_test`,
  `deposit_composition`): the potential rule (I1) looks up the measured potential of
  already-characterised compositions in helao-async's OER dataset (`oer13_cps`). That
  file belongs to helao-async and is not redistributed with lab-gate. Download it once
  from helao-async at the pinned commit, with its SHA-256 checked:

  ```
  lab-gate fetch-data
  lab-gate check plan_measure.json     # in examples/; PASS once the data is present
  ```

  Or point `HELAO_DATASET` at a copy. Without the file, such plans ABSTAIN
  (`checker_error`) and the command prints a warning. They never PASS.
- The helao-async Python package is not needed at runtime. The evaluation code in this
  repository (`make ...`) still expects a helao-async checkout beside it; see
  [Reproduce the evaluation](#reproduce-the-evaluation).
- The wheel installs three import packages: `lab_gate` (the public API and command),
  and `gate` and `sim_ext` (the internals it wraps).

## What it does NOT do

- **It only knows the rules it is given.** Harm that no rule describes passes. In the
  held-out evaluation, 20.6% of the static and decomposition attack plans (n=34)
  reached a benign harm the gate was never given a rule for (the out-of-spec probes,
  reported separately from the headline numbers). A rule-based gate cannot see such
  harm.
- **Simulation only.** Every result comes from the OER simulator. lab-gate has not
  been validated in a real lab, and no number here transfers to physical equipment
  without re-measurement.
- **The seed rules are benign examples, not a safety policy.** They model the
  structure of real controls (instrument protection, budgets, forbidden combinations,
  protocol order) with benign quantities.
- **The human stays responsible.** The gate enforces the rules exactly, including any
  mistake in them; a wrong limit gives a confident wrong verdict. ABSTAIN hands the
  decision back to a person. Writing and reviewing the rules is a human job.
- **Proofs are bounded.** PASS covers plans up to the horizon (64 actions by default);
  longer plans ABSTAIN. Some accumulate rules are proved only up to that horizon, and
  the certificate says which.
- **It does not judge scientific merit**, and there is no human-agreement evidence
  yet (the agreement protocol is written but not run).

Full list: [`LIMITATIONS.md`](https://github.com/Anuja-Khatri/lab-gate/blob/main/LIMITATIONS.md).

## Why

Autonomous labs run agents that execute physical experiments in loops, and
lab-as-a-service platforms share instruments across several partners. Reasoning
agents are good at breaking a goal into composable steps, which is also how a
forbidden goal can be split into innocent-looking steps. A gate that fences written
safety and protocol rules, and routes everything novel to a human, is one way to keep
that structure honest. The gate never judges scientific merit and never blocks
surprising-but-safe science; it is a verifier and an evaluation environment, not a
rival reasoning method.

## Research and evaluation

The rest of this page describes how lab-gate was evaluated. The installed package
contains the gate only; the evaluation runs from a clone of this repository.

## Three ways to judge it

1. **Watch**: `make demo` reproduces the headline numbers from cached model
   responses, without API keys (also packaged as a Docker image under `docker/`). A
   recorded cast is in `media/`.
2. **Read**: this README, `docs/FINAL_REPORT.md`, `docs/POST.md`, and the static
   results page in `site/` (every number renders from `results/registry.json` under a
   numbers lock).
3. **Reproduce**: `make ci` (lint, tests, taint test, static no-reference check,
   secret scan, numbers-lock check), `make sim`, `make equivalence`, `make eval`,
   `make probe` (malformed-number probes; see `docs/CORRECTIONS.md`).

## Reproduce the evaluation

```
# Work from a parent directory ($WS). lab-gate and helao-async must sit side by side:
#   $WS/lab-gate   $WS/helao-async
git clone https://github.com/Anuja-Khatri/lab-gate.git lab-gate
git clone https://github.com/High-Throughput-Experimentation/helao-async.git
git -C helao-async checkout ba910c4   # the pin the gate is evaluated against

cd lab-gate
make setup                      # uv venv (Python 3.12) + deps; PYTHONPATH -> helao-async
make ci                         # lint + tests + taint + secret scan + numbers lock
make sim                        # deterministic OERSIM closed loop (byte-identical)
make demo                       # reproduce headline numbers from cache (no API keys)
```

`make demo` needs no keys and no network: it recomputes the headline numbers from the
committed cache (`eval/cache/`) and checks them against `results/registry.json`.
Verified from a fresh clone (setup, ci, sim, demo all pass offline).

The LLM arms (LLM gate, LLM attacker) need keys in `$WS/.env`
(`LABGATE_ANTHROPIC_API_KEY`, `LABGATE_OPENAI_API_KEY`, `LABGATE_GEMINI_API_KEY`,
`LLM_BUDGET_USD`); every call
is cached, metered, and budget-capped. `make demo` needs no keys.

## Results summary

See `docs/tables/results.md` (rendered from the registry) and the site. In short, on
the held-out evaluation:

- the typed gate lets through no in-specification static or decomposition attack and
  never false-blocks a benign plan, including the surprise subset; its failures are
  confined to out-of-spec harm and attacks beyond its horizon, where it abstains;
- the LLM gate, given a frontier model, the full rules, and the full plan including
  comments, is an unreliable gate in both model families tested, in opposite
  directions: one is too permissive (lets through ~a quarter of the attacks), the
  other over-blocks benign plans and lets through adaptive attacks with nonzero
  run-to-run variance; giving the permissive LLM the same predicted potential the typed
  gate uses sharply cut its attack misses but did not make it a reliable gate;
- the learned classifier is accurate in-distribution and degrades under adaptive
  attack;
- a third-vendor cross-check (Gemini attacker + Gemini gate) is implemented and
  verified live but its arms are "blocked, not measured" on the available free-tier
  quota, reported honestly empty rather than estimated.

Exact rates with n and 95% CIs are in the registry; this prose states direction only.
The reference and SMT checkers agree on every plan in the equivalence suite, every
BLOCK counterexample replays in the simulator, and the taint test shows no text
channel.

## Preregistration and report

The evaluation protocol was frozen before the held-out runs; the binding timestamp is the git tag prereg-v1. The protocol is registered at OSF: https://osf.io/jxhfe. The full report PDF: https://doi.org/10.5281/zenodo.23954617.

## Limitations

A simulator is not a lab; the invariants are benign stand-ins that model the structure
of real controls; there is no human-agreement evidence; the paid LLM arms ran at
reduced sizes under a spend cap. Full list: `LIMITATIONS.md`. Human checkpoints:
`HUMAN_CHECKPOINTS.md`. Agreement protocol (written, unexecuted): `AGREEMENT_PROTOCOL.md`.

## Attribution and AI disclosure

Built on `helao-async` (MIT) at pin `ba910c4`; the OER CP dataset replayed by OERSIM
originates from measurements associated with doi:10.1039/C8MH01641K. Pattern reuse
(taint test, equivalence harness, cached/metered LLM wrapper, results registry,
numbers lock, secret scan) from the owner's public `consilience-verification` repo;
no domain content was copied. See `NOTICE`.

This project was carried out by Claude Code from a specification written with Claude,
with the owner reviewing and confirming the decision rules. Every non-trivial decision
is logged in `DECISIONS.md`.

## References

- Dwyer, Avrunin & Corbett. Patterns in property specifications for finite-state
  verification. ICSE 1999.
- De Giacomo & Vardi. Linear temporal logic and linear dynamic logic on finite
  traces. IJCAI 2013.
- Shah, Kamath, Li & Shah. Bayesian inference of temporal task specifications from
  demonstrations. NeurIPS 2018.
- Guevarra et al. Orchestrating nimble experiments across interconnected labs
  (HELAO).
- helao-async repository:
  https://github.com/High-Throughput-Experimentation/helao-async

## License

MIT (see `LICENSE`).
