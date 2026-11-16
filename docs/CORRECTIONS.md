# Corrections

Changed values are never silent. This file records every metric whose value changed
under the corrected verdict scoring (D-030/D-031), the old values preserved, and the
per-arm truncation rates from the free re-scoring pass (round 3d, item 0). The current
values live in `results/registry.json`.

## The defect (D-030)

The Anthropic (opus) gate calls were sent with `max_tokens=400`. opus-5-5 is a
reasoning model: it spent that budget on thinking and returned empty/truncated text
that did not parse as the strict-JSON verdict. The old parser mapped unparseable
output to ABSTAIN -- scoring an ERROR as a verdict. So round-2's opus arms were a
truncation artifact. Fix: an adequate output budget for reasoning models, unparseable
-> ERROR (scored as reduced n, never a verdict), enforced by
`tests/test_error_scoring.py`.

## Per-arm truncation rates (free re-scoring over the cache, no API)

| arm | truncation (unparseable) rate | clean? |
|---|---|---|
| gpt-5.1 gate, benign (n=300 cached) | 0.000 | yes |
| gpt-5.1 variance repeats (n=180 cached) | 0.000 | yes |
| opus gate PRE-FIX, benign (max_tokens=400) | 0.900 | NO -- artifact |
| opus gate POST-FIX, benign (max_tokens=2048) | 0.000 | yes (corrected) |

gpt-5.1 used an adequate completion budget throughout, so every gpt-5.1 metric is
unchanged under corrected scoring (verified). The opus pre-fix runs (90% truncation)
were re-run on live Anthropic with the fix and reduced-n discipline.

## Metrics changed under corrected scoring (opus arms; old -> new)

| metric | OLD (round-2, truncation artifact) | NEW (corrected, D-030/3c) |
|---|---|---|
| abstain.llm.benign | 0.901 (n=294) | 0.003 (n=294) |
| falseblock.llm.benign | 0.000 (n=294) | 0.003 (n=294) |
| attack.llm.static_decomp | 0.108 (n=37) | 0.278 (n=36) |
| attack.llm.adaptive | 0.000 (n=36) | 0.278 (n=36) |
| abstain.llm_parity.benign | 0.918 (n=294) | 0.000 (n=293) |
| falseblock.llm_parity.benign | 0.000 (n=294) | 0.003 (n=293) |
| attack.llm_parity.static_decomp | 0.081 (n=37) | 0.083 (n=36) |

Interpretation change: the old numbers described the opus gate as massively
over-abstaining (0.90); that reading was an artifact. The corrected opus gate is
PERMISSIVE -- it decides essentially every benign plan (abstain 0.003) but lets through
0.28 of the static+decomposition attacks; information parity cuts that to 0.03.

## Unchanged (verified clean under corrected scoring)

- All gpt-5.1 metrics: `falseblock.llm_gpt51.benign` 0.643, `attack.llm_gpt51.static_decomp`
  0.108, `attack.llm_gpt51.adaptive` 0.458, `variance.llm_gpt51.flip_rate` 0.30
  (0% truncation; the earlier over-blocking finding stands).
- `falseblock.llm.surprise` 0.000 (opus post-fix, clean).
- The deterministic arms (typed gate, classifier, oracle, programmatic attacker,
  equivalence, replay, taint, latency) never involved an LLM and are unaffected.

## Still blocked, not measured (not corrections; no backfill)

See LIMITATIONS.md and FINAL_REPORT.md Section 6: the OpenAI gpt-5.1 tails (no credits)
and, where a run did not complete, the Anthropic attacker / variance tails; and the
Gemini arms (free-tier quota). These carry null values with "blocked, not measured"
caveats and exact n, never backfilled.

## 2026-11-16: malformed numbers and NaN refused at the boundary (input fix)

**What was wrong.** Probing outside the preregistered suites found quantity inputs
the typed gate read wrongly or crashed on. `"1 200 degC"` was read as 200 (pint
treats the space as multiplication), `"1.2.3 degC"` as 0.36, and `"nan degC"`,
`"-inf degC"`, a float NaN and a `{"value": NaN, "unit": "degC"}` mapping were all
accepted; each of those plans received PASS with a proof certificate. A NaN deposit
thickness made `decide()` raise an uncaught solver exception instead of returning a
verdict. The oracle shares the same parser, so the repository's own scoring did not
count these as attack successes.

**Fix.** `gate/boundary/units.py` now accepts a quantity string only as one plain
decimal number plus an optional unit (no spaces, commas, second decimal point,
brackets or arithmetic inside the number; digits in the unit only as exponents) and
refuses NaN and infinity in every form. Every action schema sets
`allow_inf_nan=False`. `decide()` turns any checker exception into ABSTAIN
`checker_error`. Each malformed plan is now ABSTAIN `schema_invalid` with a detail
naming the problem, the same handling the gate already gave unit mismatches. Tests:
`tests/test_malformed_numbers.py`.

**Probe suite.** The ten probe plans are in `eval/redteam/malformed.py` and run with
`make probe` (offline, deterministic arms only); results in
`results/probe_malformed.json`. They are kept out of `static.all_static()` because
that suite is frozen by the preregistration and the cached LLM-gate responses are
keyed to its exact plans; adding to it would change the published n of every arm and
could not be re-run for the LLM arms without paid calls.

| typed gate on the 10 probes | before the fix | after the fix |
|---|---|---|
| PASS with proof certificate | 6 | 0 |
| BLOCK | 1 (float +inf, read as over the limit) | 0 |
| ABSTAIN | 1 (bare `"inf"`, no unit) | 10 |
| uncaught exception | 2 (NaN thickness) | 0 |

The learned classifier baseline (not a deployed gate; a comparison arm) blocked two
of the ten before the fix (the +inf anneal and the NaN-thickness Ce/Mn deposit) and
passes all ten after it: its features are computed from the same boundary parse, so
a refused plan now reaches it with no typed actions. This does not affect any
published classifier number (see below).

**Published numbers.** No published number changes because of this fix. The
offline re-run (`make demo`, which passed, and `python -m eval.heldout` with no API
keys, so only the deterministic arms ran) gave every typed-gate metric
exactly as registered, including `attack.typed.static_decomp` 0.0 (n=37),
`falseblock.typed.benign`, `falseblock.typed.surprise`, `abstain.typed.benign`,
`abstain_breakdown.typed` and `attack.typed.adaptive`. The numbers lock is
unchanged.

**Found while re-running, not caused by this fix.** The classifier baseline's
adaptive arm does not reproduce exactly. `attack.classifier.adaptive` is registered
as 0.316667 (n=240); two offline re-runs, one on the code before this fix and one
after, both gave 0.308333 (n=240), and the per-budget points of
`attack_curve.classifier` differed between those two runs. The registry value is
left as recorded until the source of the run-to-run variation is found; it affects
a comparison baseline, not the typed gate. The offline driver also crashed at its
last step on a missing `logs/cost_meter.json`; that is fixed (the registered spend
is left unchanged when nothing was metered).
