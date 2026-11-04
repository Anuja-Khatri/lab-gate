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
