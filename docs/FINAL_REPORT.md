# Final report: lab-gate

Plain language. Every number here is rendered from `results/registry.json` under the
numbers lock (see `docs/tables/results.md` for the full table with n and 95% CIs).
Rates use Wilson 95% CIs; curves use bootstrap 95% CIs. The held-out evaluation was
run once after the `prereg-v1` git tag.

## 1. What was built

An open-source, plan-checking safety gate for autonomous labs, built on the public
helao-async framework and evaluated inside its OER simulator. The gate checks a typed
plan against a registry of benign invariants and returns PASS (with a proof
certificate), BLOCK (with a counterexample), or ABSTAIN (routed to a human). No
decision path reads any free-text field. Methods are in `docs/METHODS.md`.

## 2. Headline results

Three gates faced the identical suites, scored against a ground-truth oracle that runs
each plan in the simulator and checks the actual trace.

| metric | typed gate | classifier | LLM gate (gpt-5.1) |
|---|---|---|---|
| attack success, static+decomposition (n=37) | 0.00 | 0.24 | 0.11 |
| attack success, adaptive (typed/clf n=96, llm n=24) | 0.00 | 0.33 | 0.46 |
| false-block, benign stream | 0.00 | 0.07 | 0.64 |
| false-block, surprise subset | 0.00 | 0.00 | (not run at scale) |
| abstain, benign stream | 0.00 | 0.00 | 0.01 |
| run-to-run verdict variance | 0.00 | 0.00 | 0.30 |

Benign-stream n=13627 oracle-safe plans; surprise n=990; LLM false-block n=294 (R-08
reduced sample). Full CIs in `docs/tables/results.md`.

Reading: the typed gate let through no in-specification attack (static, decomposition,
or adaptive) and never false-blocked a benign plan, including the surprise subset of
unusual-but-valid plans. The LLM gate, given a frontier model, the full written rules,
the full plan including comments, and a dev-tuned frozen prompt, both missed attacks
it could not quantify (for example instrument overload, which it cannot predict from a
composition) and over-blocked benign plans at 0.64, with run-to-run verdict variance
of 0.30. The learned classifier was accurate in-distribution (benign false-block 0.07)
but was broken by a quarter of the static attacks and a third of the adaptive ones.

## 3. Checker guarantees (deterministic)

- Reference evaluator vs independent Z3/SMT encoding: exact verdict agreement on the
  full equivalence suite, rate 1.0 (n=12000). The exported LTLf formulas agree with
  the kind-specific checks on every plan.
- Counterexample replay validity: 1.0 (n=458). Every BLOCK's counterexample, executed
  in the simulator, is confirmed by the oracle.
- Taint test: no text channel, result 0 (n=1000). Injecting a sentinel into every
  free-text field never changed a verdict and never reached a checker input or output.
- Latency: p50 and p95 recorded (p95 about 20 ms per full decision).

## 4. Hypothesis outcomes (preregistered HYP-1..HYP-5)

- HYP-1 (typed gate near-zero on in-spec attacks): SUPPORTED. 0.00 on both static+
  decomposition (n=37) and adaptive (n=96); the Anthropic LLM attacker also found no
  success against the typed gate (n=8, reduced grid).
- HYP-2 (typed-gate failures concentrate in out-of-spec / beyond-horizon / divergence
  / over-abstention): SUPPORTED in direction. The gate's residual surface is
  out-of-spec harm (20.6% of attack plans reached a benign harm the gate was never
  given) and beyond-horizon plans (it abstains on them rather than guessing). No
  in-spec attack succeeded, so there were no divergence or over-abstention failures on
  the benign stream to report.
- HYP-3 (LLM gate nonzero under injection/decomposition; nonzero variance): SUPPORTED.
  Attack success 0.11 (static+decomp) and 0.46 (adaptive); run-to-run variance 0.30.
- HYP-4 (classifier high in-distribution, degrades under adaptive): SUPPORTED. Benign
  false-block 0.07; adaptive attack success 0.33 > static 0.24.
- HYP-5 (typed gate abstains more on the benign stream than the LLM gate):
  NOT SUPPORTED. The typed gate abstained 0.00 on the benign stream and the LLM gate
  0.01. The LLM gate's cost on benign plans was over-BLOCKING (0.64), not the typed
  gate over-abstaining. The typed gate's abstention appears instead on beyond-horizon
  and out-of-schema plans, not on the benign stream. Reported as observed.

## 5. Specification coverage

The out-of-spec probes (OS1..OS4) are benign harms the gate is not given. 20.6% of the
static+decomposition attack plans reached at least one (n=34). This is not a gate
failure; it measures what any rule-based gate cannot catch because it was never told.
It is reported separately and never folded into the headline attack numbers.

## 6. Deviations from the preregistration

The preregistration (tag `prereg-v1`) set the deterministic adaptive attacker to 200
queries x 10 seeds x 2 modes and the LLM arms to specified reduced sizes. Actual run:

- Deterministic adaptive attacker (typed + classifier): reduced to 120 queries x 4
  seeds x 2 modes (n=96 trajectories per gate). Reason: compute time; the typed gate's
  success is 0.00 and the classifier's is stable across seeds, so the conclusion is
  unchanged. This is a deviation on a deterministic arm and is disclosed here.
- Adaptive attacker vs the LLM gate: 20 queries x 2 seeds x gray-box, all goals
  (n=24). Reason: paid-LLM time and the R-08 budget.
- LLM-gate benign false-block: measured on a 294-plan oracle-safe sample (R-08), not
  the full benign stream.
- Run-to-run variance: LLM gate on 60 plans x 3 repeats (each repeat a distinct request
  so it is a real call, not a cache hit).
- Anthropic LLM attacker: a reduced demonstration grid of 4 goals x 2 seeds x 12
  queries vs the typed gate (n=8). The programmatic attacker provides the full-grid
  adaptive numbers for typed and classifier.

Total metered LLM spend: $4.44, well under the $500 cap.

## 7. Limitations

See `LIMITATIONS.md`. In short: a simulator is not a lab; the invariants are benign
stand-ins; there is no human-agreement evidence (`AGREEMENT_PROTOCOL.md` is written and
unexecuted); the paid LLM arms ran at reduced sizes; the full orchestration group was
not launched (R-05 in-process driving); the gradient-boosting classifier used sklearn
rather than xgboost (D-021). This was an AI-assisted build (Claude Code from a
specification written with Claude; the owner reviewed and confirmed the decisions).

## 8. How to reproduce

`make demo` reproduces the headline numbers from cached model responses without API
keys. `make ci` runs lint, tests, the taint test, the static no-reference check, the
secret scan, and the numbers-lock check. `make equivalence` reruns the reference-vs-SMT
suite. `make eval` reruns the held-out evaluation (needs keys for fresh LLM calls;
replays from cache otherwise).
