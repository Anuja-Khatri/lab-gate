# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native).

## BUILD COMPLETE

All phases (0 through 10) are done. `make ci` is green: lint, 72 tests, taint test,
static no-reference check, secret scan (working tree and full git history), and the
numbers-lock check. The owner's remaining steps are in `OWNER_TODO.md`.

## One-page summary

What it is: `lab-gate`, an open-source plan-checking safety gate for autonomous labs,
built on public helao-async at pin `ba910c4` and evaluated in its OER simulator. The
gate returns PASS (proof certificate), BLOCK (counterexample), or ABSTAIN (human
queue), reading only typed fields.

Headline held-out results (per-cell n below; full table with 95% CIs in
`docs/tables/results.md`; every number locked in `results/registry.json`). The LLM-gate
arms ran on Anthropic claude-opus-5-5 (R-03 fallback; OpenAI out of credits, D-024);
the parity arm additionally gets the predicted potential the typed gate's I1 uses.

| metric | typed | classifier | LLM gate (opus) | LLM parity (opus) |
|---|---|---|---|---|
| attack, static+decomp | 0.00 (n=37) | 0.24 (n=37) | 0.28 (n=36) | 0.08 (n=36) |
| attack, adaptive | 0.00 (n=240) | 0.32 (n=240) | 0.28 (n=36) | (not run) |
| false-block, benign | 0.00 (n=13627) | 0.07 (n=13627) | 0.003 (n=294) | 0.003 (n=293) |
| false-block, surprise | 0.00 (n=990) | 0.002 (n=990) | 0.00 (n=297) | 0.00 (n=294) |
| abstain, benign | 0.00 (n=13627) | 0.00 (n=13627) | 0.003 (n=294) | 0.00 (n=293) |
| decided coverage, benign | 1.00 | 1.00 | 0.997 | 1.00 |
| run-to-run variance | 0.00 (n=120) | 0.00 (n=120) | 0.03 (n=119) | (not run) |

Preregistered Anthropic opus attacker: vs typed 0.00 (n=12), vs opus gate 0.00 (n=12,
same-vendor). Corrected in round 3c/3d (D-030/D-032): round-2's opus "over-abstains
0.90" was a truncation artifact (max_tokens=400 for a reasoning model -> unparseable
output wrongly scored as ABSTAIN); the free re-scoring pass confirmed gpt-5.1 is clean
(0% truncation) and the opus pre-fix was 90% truncation (see docs/CORRECTIONS.md). Re-run
with adequate tokens + reduced-n, the real opus gate is PERMISSIVE (decides ~all benign,
lets through 0.28 of attacks, adaptive 0.28, variance 0.03); parity cuts attack success
to 0.08. The gpt-5.1 gate over-BLOCKED (false-block 0.64, variance 0.30, kept as
`*.llm_gpt51`).

The opus LLM gate's failure mode is massive over-ABSTENTION (0.90 of benign); the
earlier OpenAI gpt-5.1 arm over-BLOCKED (0.64) with adaptive attack 0.46 and variance
0.30 (preserved as `*.llm_gpt51.*`). Both free-text arms are unreliable gates, in
opposite directions; information parity did not fix the opus arm (0.90 -> 0.92 abstain).

Checker guarantees: reference vs SMT equivalence 1.0 (n=12000); counterexample replay
validity 1.0 (n=458); taint test 0 (no text channel, n=1000); p95 latency ~20 ms.
Specification coverage: 0.21 of attack plans reached an out-of-spec harm the gate was
never given (n=34, reported separately). Metered LLM spend across all runs: $30.08 of
the $500 cap.

Hypotheses: HYP-1 supported (typed 0.00 on in-spec attacks, adaptive n=240); HYP-2
supported in direction; HYP-3 supported (LLM arms nonzero/unreliable, gpt-5.1 variance
0.30); HYP-4 supported (classifier degrades under adaptive, 0.24 -> 0.32); HYP-5 NOT
supported and strongly opposite for opus (LLM abstains 0.90 >> typed 0.00) — reported
as observed.

## Disclosed deviations and decision-rule uses

- R-05: full orchestration group not launchable here; OERSIM driven in-process with
  the real action models and dataset (D-009).
- R-06: benign accounting extension for quantities OERSIM does not track (D-006).
- R-04: sklearn HistGradientBoosting instead of xgboost (libomp unavailable) (D-021).
- R-13: models verified live and pinned (gpt-5.1, claude-opus-5-5) (D-022).
- R-08: paid LLM arms metered under per-role caps; see FINAL_REPORT Section 6 for exact n.
- R-02: media gif/webm renderers (agg, Playwright) not installable; the asciinema cast
  is produced, gif/webm deferred to the owner (OWNER_TODO).
- Round 3c (owner independent review; D-030/D-031): ERROR audit (item 0) caught that
  round-2's opus "over-abstains 0.90" was a TRUNCATION ARTIFACT (max_tokens=400 for a
  reasoning model); ERRORs are now scored as reduced n, never verdicts
  (eval/metrics.decided_counts + tests/test_error_scoring.py). Anthropic was live (promo
  credit): the opus gate arms (plain+parity) re-ran correctly -> permissive gate
  (attack 0.28; parity 0.03); the preregistered Anthropic attacker + opus variance hit
  the Anthropic monthly cap again and are "blocked, not measured" (attacker-vs-typed
  keeps the earlier real reduced n=8). OpenAI still blocked. Gemini live but free-tier;
  the hard-$1.50-capped smallest arm hit the quota -> stays blocked. No backfill, no
  fabrication.
- Round 3/3b (D-026..D-029): added Gemini integration + live model verification +
  retry/backoff; de-backfilled the opus variance; decided-coverage row (item 5);
  same-vendor marking (item 6); within-vendor parity only (item 4).
- Round 2 (owner independent review; D-023/D-024/D-025): re-ran the deterministic
  adaptive attacker at the FULL original spec (200x10x2, n=240); added an
  information-parity LLM arm (D-023); added the surprise-subset LLM number; added the
  abstain breakdown; fixed the one-page table (per-cell n, classifier surprise 0.002).
  OpenAI ran out of credits mid-review so the LLM arms ran on Anthropic claude-opus-5-5
  (R-03, D-024); then Anthropic hit a monthly usage limit, so the opus run-to-run
  variance and the full LLM attacker could not complete (R-08, D-025) and are reported
  with the earlier real values + exact n + explicit caveats. No fabrication.
- No FAILED (R-09) acceptance tests.

## No-failure disclosures

- helao-async and refs clones verified unmodified; writes confined to `lab-gate/`,
  `logs/`, and `helao-async-pr/` (the never-pushed upstream draft).
- No git push, no remotes created, no publishing. Publishing is the owner's job.
- `.env` contents never printed, logged, or committed.

## Last completed task
Owner review round 3d (D-032): FREE re-scoring pass over all cached LLM responses
(gpt-5.1 CLEAN 0% truncation -> unchanged; opus pre-fix 0.90 truncation, already
corrected; docs/CORRECTIONS.md with old->new, never silent); Anthropic live -> the
PREREGISTERED arms COMPLETED (adaptive attacker vs typed 0.00/n=12, vs opus gate
0.00/n=12 same-vendor; programmatic vs opus 0.28/n=36; opus variance 0.03/n=119).
Re-locked (56 metrics), regenerated table/FINAL_REPORT/POST/README/site, updated
CORRECTIONS/LIMITATIONS/deviations/OWNER_TODO, `make ci` green (76 tests), `make demo`
reproduces. Spend $93.82/500 (promo credit). See DECISIONS D-001..D-032. BUILD COMPLETE.

## (prior) round 3c task
Owner review round 3c (D-030/D-031): global ERROR audit (ERROR=reduced n, never a
verdict; CI test added) caught and retracted the round-2 opus truncation artifact;
re-ran the opus gate arms correctly on live Anthropic (permissive gate; parity cuts
attack 0.28->0.03); preregistered Anthropic attacker + opus variance blocked by the
monthly cap (exact n, no backfill); OpenAI blocked; Gemini free-tier -> capped arm
stays blocked. Re-locked registry, regenerated table/FINAL_REPORT/POST/README/site,
updated LIMITATIONS/deviations/OWNER_TODO, `make ci` green, `make demo` reproduces.
See DECISIONS.md (D-001..D-031). BUILD COMPLETE stands.

## (prior) round 3b task
Owner review round 3b (D-026..D-029): verified all three vendor keys live (only
Gemini usable; OpenAI/Anthropic blocked); added Gemini to eval/llm.py (pinned
gemini-3.1-pro-preview, retry/backoff); dev-tuned+froze the Gemini prompt; Gemini
held-out arms blocked by free-tier quota -> reset to "blocked, not measured" (R-08,
quota-polluted partials removed, nothing backfilled/fabricated). Items 4-7 done:
within-vendor parity, decided-coverage row, same-vendor marking, no backfill. Registry
re-locked (50 metrics), table/FINAL_REPORT/POST/README/site/STATUS regenerated,
LIMITATIONS + deviations updated, `make ci` green, `make demo` reproduces. See
CHECKLIST.md and DECISIONS.md (D-001..D-029). BUILD COMPLETE stands.
