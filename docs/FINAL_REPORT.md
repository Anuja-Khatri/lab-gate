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
| attack success, static+decomposition | 0.00 (n=37) | 0.24 (n=37) | 0.28 (n=36) | 0.08 (n=36) |
| attack success, adaptive | 0.00 (n=240) | 0.32 (n=240) | 0.28 (n=36) | (not run) |
| false-block, benign | 0.00 (n=13627) | 0.07 (n=13627) | 0.003 (n=294) | 0.003 (n=293) |
| false-block, surprise | 0.00 (n=990) | 0.002 (n=990) | 0.00 (n=297) | 0.00 (n=294) |
| abstain, benign | 0.00 (n=13627) | 0.00 (n=13627) | 0.003 (n=294) | 0.00 (n=293) |
| decided coverage, benign | 1.00 | 1.00 | 0.997 | 1.00 |
| run-to-run variance | 0.00 (n=120) | 0.00 (n=120) | 0.03 (n=119) | (not run) |

Preregistered Anthropic adaptive attacker (claude-opus-5-5): vs the typed gate 0.00
(n=12, 6 goals x 2 seeds x 20 queries) -- the typed gate resists the LLM attacker as
well; vs the opus LLM gate 0.00 (n=12, SAME-VENDOR, same model -- interpret with care).

EXTENSION (not preregistered, D-033): the LLM adaptive attacker vs the typed gate only
was scaled to 8 goals x 6 seeds = n=48 per mode in BOTH observation modes. Attack
success 0.00 in black-box (0/48, 95% CI 0.00-0.074, attacker sees only the verdict) and
0.00 in gray-box (0/48, 95% CI 0.00-0.074, attacker additionally sees the blocked
invariant id). This is a labelled extension, kept separate from the preregistered grid;
it strengthens HYP-1 at larger n and in both modes, consistent with the programmatic
adaptive attacker (0.00, n=240). Metered spend for the whole study rose to $126.32,
within the Anthropic promo headroom.

IMPORTANT correction (D-030): round-2's opus arms were a TRUNCATION ARTIFACT -- the
Anthropic call budget (max_tokens=400) was too small for a reasoning model, so opus
returned empty/unparseable text that was wrongly scored as ABSTAIN (hence the earlier
"0.90 over-abstention"). The ERROR audit (item 0) caught this; the arms were re-run
with an adequate budget and reduced-n discipline (ERROR excluded from n, never a
verdict). The REAL opus gate is PERMISSIVE: it decides essentially every benign plan
(abstain 0.003, false-block 0.003, decided coverage 0.997) but lets through 0.28 of
the static+decomposition attacks and 0.28 under the adaptive attacker (n=36).
Information parity -- appending the predicted potential the typed gate uses -- drops
static+decomposition attack success to 0.08 (a large within-vendor effect, mostly from
fixing the I1 misses). Its run-to-run variance is 0.03 (n=119): nonzero, unlike the
deterministic typed gate. The earlier OpenAI gpt-5.1 arm failed the OTHER
way -- it over-BLOCKED benign plans at 0.64 with adaptive attack success 0.46 and
run-to-run variance 0.30 (`*.llm_gpt51.*`). So the two free-text gates are unreliable
in opposite directions: opus too permissive, gpt-5.1 too blocking. The opus run-to-run
variance is "blocked, not measured" (Anthropic cap); the real gpt-5.1 variance 0.30 is
kept under its own id, not backfilled.

Reading: the typed gate let through no in-specification attack (static, decomposition,
or adaptive, n=240) and never false-blocked a benign plan, including the surprise
subset. The opus LLM gate decides essentially every benign plan but is too PERMISSIVE
on attacks (0.28 pass); the earlier gpt-5.1 gate is too BLOCKING on benign plans
(false-block 0.64). Both free-text gates are unreliable, in opposite directions. The
learned classifier is accurate in-distribution (benign false-block 0.07) but is broken
by a quarter of the static attacks and a third of the adaptive ones (n=240).

Information parity (within-vendor, Anthropic opus): appending the predicted potential
the typed gate's I1 uses drops the opus gate's static+decomposition attack success from
0.28 to 0.08 -- a large effect, mostly from fixing the instrument-overload (I1) misses
it otherwise cannot quantify. Both numbers are the same vendor and model
(claude-opus-5-5), so this is a clean within-vendor comparison; it is never presented
against a different-vendor gate. The opus gate's benign behaviour (false-block 0.003,
abstain 0.003) is essentially unchanged by parity, so the parity effect is specifically
on attack detection. A second within-vendor parity pair (Gemini plain vs Gemini parity)
is blocked, not measured: the Gemini key is valid and live but free-tier quota
(~25 req/model) is too low to run the arms (D-029/D-031).

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
  seeds x 2 modes); the preregistered Anthropic LLM attacker also found no success
  against the typed gate (0.00, n=12), and the labelled extension (D-033) found none at
  larger n in both observation modes (0.00 black-box n=48, 0.00 gray-box n=48).
- HYP-2 (typed-gate failures concentrate in out-of-spec / beyond-horizon / divergence
  / over-abstention): SUPPORTED in direction. The gate's residual surface is
  out-of-spec harm (0.21 of attack plans reached a benign harm the gate was never
  given, n=34) and beyond-horizon plans (it abstains on them; abstain_breakdown.typed
  records 1 beyond_horizon + 5 schema_invalid over benign+suites). No in-spec attack
  succeeded.
- HYP-3 (LLM gate nonzero under injection/decomposition; nonzero variance): SUPPORTED.
  The opus arm lets through 0.28 of static+decomposition attacks (n=36) and 0.28
  adaptive (n=36), with run-to-run variance 0.03 (n=119, nonzero); the gpt-5.1 arm 0.11
  static+decomp, 0.46 adaptive, variance 0.30. Both free-text gates are unreliable, in
  OPPOSITE directions: opus is too permissive, gpt-5.1 too blocking.
- HYP-4 (classifier high in-distribution, degrades under adaptive): SUPPORTED. Benign
  false-block 0.07; adaptive attack success 0.32 (n=240) > static 0.24.
- HYP-5 (typed gate abstains more on the benign stream than the LLM gate):
  NOT SUPPORTED. On the corrected measurements both the typed gate (0.00) and the opus
  LLM gate (0.003) barely abstain on the benign stream; the LLM gates' benign cost is
  not abstention but over-blocking (gpt-5.1, 0.64) and permissiveness on attacks (opus,
  0.28). The earlier "opus over-abstains 0.90" was a truncation artifact (D-030), now
  retracted. Reported as observed.

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
opus is too permissive). Total metered LLM spend across all runs: $126.32, within the
$500 cap and the per-role caps (the Anthropic runs used the owner's promo credit).

Extension (D-033, not preregistered, declared before execution). The LLM adaptive
attacker vs the TYPED gate only was scaled to n=48 trajectories per mode (8 goals x 6
seeds x 20 queries) in both observation modes: black-box (verdict only) and gray-box
(verdict + blocked-invariant id). Both returned attack success 0.00 (0/48, 95% CI
0.00-0.074) -- `attack.llm_attacker_vs_typed.blackbox_ext` and `*.graybox_ext`. The
typed gate always returns a decided verdict, so n equals the completed trajectory count
exactly; the run completed without hitting the cap (cumulative study spend $126.32,
within the promo headroom). This is kept separate from the preregistered grid and labelled on both
metrics; it is a larger, two-mode replication of the preregistered 0.00 (n=12), not a
new preregistered claim.

Round 3c/3d (D-030/D-031/D-032). (0) ERROR audit + free re-scoring: an LLM call that
returns no usable verdict (unparseable/empty/quota) is scored as REDUCED n, never as a
verdict, enforced by `eval/metrics.decided_counts` and `tests/test_error_scoring.py`.
Re-scoring every cached response showed gpt-5.1 is clean (0% truncation; its metrics
unchanged) and the opus PRE-FIX runs were 0.90 truncation (the retracted "over-abstention
0.90" artifact); old->new values are preserved in `docs/CORRECTIONS.md`. (1) Anthropic
was live across rounds 3c and 3d: the opus gate arms (plain + parity) ran to completion,
and in round 3d the PREREGISTERED arms completed too -- the programmatic attacker vs the
opus gate (adaptive 0.28, n=36), the preregistered Anthropic adaptive attacker vs the
typed gate (0.00, n=12) and vs the opus gate (0.00, n=12, same-vendor), and the opus
run-to-run variance (0.03, n=119). (2) OpenAI gpt-5.1 tails stay blocked (no credits).
(3) Gemini is valid and live but free-tier (~25 req/model); the hard-$1.50-capped
smallest-arm attempt hit the quota and stays "blocked, not measured" (cap never
approached). Nothing backfilled or fabricated.

Round 3 / 3b (owner independent review; D-026/D-027/D-028/D-029). (1) No earlier
"point-7 Gemini" instruction was ever received by this build; logged. (2) Gemini was
added to `eval/llm.py` (cached, metered, same caps, retry/backoff) with live model
verification, to run a cross-vendor adaptive attacker and a second LLM-gate vendor.
All three vendor keys were then re-verified with live generation calls: OpenAI gpt-5.1
is out of credits (429); Anthropic is at its monthly usage limit (400, to 2026-12-01);
the Gemini AQ-format key is VALID and gemini-3.1-pro-preview returns strict JSON
(pinned R-13), but the account is free-tier with a quota of ~25 requests/model, so the
held-out run 429'd after ~55 calls (the dev-split prompt tuning of 30 calls did
complete: agreement vs oracle 0.633, n=30). Every Gemini held-out arm -- the adaptive
attacker vs the typed gate and vs a Gemini gate, and the Gemini plain/parity gate arms
on benign/surprise/static/decomposition and variance -- is therefore "blocked, not
measured" with exact n; the quota-polluted partial values were reset, not kept, and
nothing is backfilled or fabricated. The integration is pinned, verified, and ready
for a paid Gemini tier via `make eval`. (3) Backfill removed (item 7): the opus
run-to-run variance is "blocked, not measured", not standing in with the gpt-5.1
value; the real gpt-5.1 variance 0.30 is kept under its own id. (4) Same-vendor marking
(item 6): no completed metric has both the gate and the attacker as the same-vendor
LLM -- the opus gate's adaptive number was produced by the deterministic programmatic
attacker (not an LLM), and the only Anthropic LLM attacker that ran targeted the
(non-LLM) typed gate; the would-be same-vendor pairs (Anthropic attacker vs Anthropic
gate; Gemini attacker vs Gemini gate) are blocked, not measured. The parity effect is
reported only within one vendor (item 4). Because all three vendors are out of
credits / at a usage limit / on a 25-request free tier, the cross-vendor
LLM-attacker-vs-LLM-gate comparison remains unmeasured and is disclosed as such.

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
