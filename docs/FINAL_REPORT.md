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

Four gate arms faced the identical suites, scored against a ground-truth oracle that
runs each plan in the simulator and checks the actual trace. Every cell shows its own
n; full CIs are in `docs/tables/results.md`. The LLM-gate arms ran on Anthropic
claude-opus-5-5 (R-03 fallback; OpenAI out of credits, D-024); the information-parity
arm additionally receives the predicted potential the typed gate's I1 uses (D-023).

| metric | typed gate | classifier | LLM gate (opus) | LLM parity (opus) |
|---|---|---|---|---|
| attack success, static+decomposition | 0.00 (n=37) | 0.24 (n=37) | 0.11 (n=37) | 0.08 (n=37) |
| attack success, adaptive | 0.00 (n=240) | 0.32 (n=240) | 0.00 (n=36) | (not run) |
| false-block, benign | 0.00 (n=13627) | 0.07 (n=13627) | 0.00 (n=294) | 0.00 (n=294) |
| false-block, surprise | 0.00 (n=990) | 0.002 (n=990) | 0.00 (n=297) | 0.00 (n=297) |
| abstain, benign | 0.00 (n=13627) | 0.00 (n=13627) | 0.90 (n=294) | 0.92 (n=294) |
| run-to-run variance | 0.00 (n=120) | 0.00 (n=120) | 0.30 (n=60) | (not run) |

Reading: the typed gate let through no in-specification attack (static, decomposition,
or adaptive, n=240) and never false-blocked a benign plan, including the surprise
subset of unusual-but-valid plans. The opus LLM gate's dominant behaviour is massive
over-ABSTENTION: it abstained on 0.90 of benign plans (0.92 for the parity arm), so its
low false-block and low adaptive attack success are artifacts of its deciding almost
nothing. The earlier OpenAI gpt-5.1 arm failed the other way: it over-BLOCKED benign
plans at 0.64 with adaptive attack success 0.46 and run-to-run variance 0.30 (preserved
as `attack.llm_gpt51.*` and `falseblock.llm_gpt51.benign`; run-to-run variance 0.30 is
the gpt-5.1 measurement, the opus variance could not be measured — see Section 6). Both
free-text arms are unreliable gates, in opposite directions. The learned classifier was
accurate in-distribution (benign false-block 0.07) but was broken by a quarter of the
static attacks and a third of the adaptive ones (n=240).

Information parity (item 2): appending the typed gate's predicted potential to the plan
JSON lowered the LLM gate's static+decomposition attack success modestly (0.11 -> 0.08)
but did not reduce its over-abstention (0.90 -> 0.92). Giving the LLM the exact quantity
the typed gate's I1 uses did not turn it into a usable gate, so its unreliability is not
merely an information deficit.

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

- HYP-1 (typed gate near-zero on in-spec attacks): SUPPORTED. 0.00 on static+
  decomposition (n=37) and 0.00 on the full adaptive grid (n=240, 200 queries x 10
  seeds x 2 modes); the earlier Anthropic LLM attacker also found no success against
  the typed gate (n=8).
- HYP-2 (typed-gate failures concentrate in out-of-spec / beyond-horizon / divergence
  / over-abstention): SUPPORTED in direction. The gate's residual surface is
  out-of-spec harm (0.21 of attack plans reached a benign harm the gate was never
  given, n=34) and beyond-horizon plans (it abstains on them; abstain_breakdown.typed
  records 1 beyond_horizon + 5 schema_invalid over benign+suites). No in-spec attack
  succeeded.
- HYP-3 (LLM gate nonzero under injection/decomposition; nonzero variance): SUPPORTED
  for the gpt-5.1 arm (static+decomp 0.11, adaptive 0.46, variance 0.30). The opus arm
  shows nonzero static+decomposition attack success (0.11) but 0.00 adaptive, because
  it abstains on ~0.90 of plans so a PASS is rare; its run-to-run variance could not be
  measured (Anthropic usage limit, Section 6). Both free-text arms are unreliable, in
  opposite directions (gpt-5.1 over-blocks, opus over-abstains).
- HYP-4 (classifier high in-distribution, degrades under adaptive): SUPPORTED. Benign
  false-block 0.07; adaptive attack success 0.32 (n=240) > static 0.24.
- HYP-5 (typed gate abstains more on the benign stream than the LLM gate):
  NOT SUPPORTED, and strongly so in the opposite direction for the opus arm. The typed
  gate abstained 0.00 on the benign stream; the opus LLM gate abstained 0.90 and the
  parity arm 0.92; the earlier gpt-5.1 arm abstained 0.01 (and over-blocked instead).
  The LLM gate abstains far MORE than the typed gate, not less. Reported as observed.

## 5. Specification coverage

The out-of-spec probes (OS1..OS4) are benign harms the gate is not given. 20.6% of the
static+decomposition attack plans reached at least one (n=34). This is not a gate
failure; it measures what any rule-based gate cannot catch because it was never told.
It is reported separately and never folded into the headline attack numbers.

## 6. Completions and deviations (round 1 and round 2)

Round 1 ran the deterministic adaptive attacker at a reduced grid and the LLM arms at
small sizes, within a spend cap. An independent round-2 review asked for the full
preregistered sizes, an information-parity LLM arm, the surprise-subset LLM number, an
abstain breakdown, and table fixes. What the round-2 run completed, and the two hard
external blockers that stopped the rest:

Completed at full size (no API): the deterministic adaptive attacker at the full
original spec, 200 queries x 10 seeds x 2 modes, for the typed gate (0.00, n=240) and
the classifier (0.32, n=240); the abstain breakdown by reason (`abstain_breakdown.typed`);
the one-page and headline tables now show per-cell n with the classifier surprise rate
as 0.002.

Completed on Anthropic claude-opus-5-5 (R-03 fallback; OpenAI ran out of credits
mid-review, D-024): the LLM gate and the information-parity LLM gate on the static+
decomposition+cross-requester suites; benign false-block/abstain on 294 oracle-safe
plans; surprise false-block on 297 oracle-safe plans (item 3, now a number for every
arm); adaptive-vs-LLM-gate at 40 queries x 3 seeds (n=36).

Not completed - Anthropic monthly usage limit reached mid-run (HTTP 400, regains
2026-12-01), D-025, R-08: (a) the opus run-to-run variance (120 x 5) - the reported
`variance.llm.flip_rate` 0.30 (n=60) is the earlier gpt-5.1 measurement, clearly
caveated; the opus variance is unmeasured. (b) The full Anthropic attacker (6 goals x 2
seeds x 20 queries vs typed AND LLM gate) - `attack.llm_attacker_vs_typed` 0.00 (n=8)
is the earlier reduced opus-attacker run; the vs-LLM-gate target did not run. These two
are reported with exact n and no extrapolation.

Vendor note: the headline LLM-gate numbers are the Anthropic opus arm (R-03). The
originally-pinned OpenAI gpt-5.1 arm is preserved as `attack.llm_gpt51.*` /
`falseblock.llm_gpt51.benign` for the vendor/model comparison (gpt-5.1 over-blocks;
opus over-abstains). Total metered LLM spend across all runs: $30.08, within the $500
cap and the per-role caps.

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
