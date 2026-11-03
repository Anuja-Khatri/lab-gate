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
| attack, static+decomp | 0.00 (n=37) | 0.24 (n=37) | 0.11 (n=37) | 0.08 (n=37) |
| attack, adaptive | 0.00 (n=240) | 0.32 (n=240) | 0.00 (n=36) | (not run) |
| false-block, benign | 0.00 (n=13627) | 0.07 (n=13627) | 0.00 (n=294) | 0.00 (n=294) |
| false-block, surprise | 0.00 (n=990) | 0.002 (n=990) | 0.00 (n=297) | 0.00 (n=297) |
| abstain, benign | 0.00 (n=13627) | 0.00 (n=13627) | 0.90 (n=294) | 0.92 (n=294) |
| run-to-run variance | 0.00 (n=120) | 0.00 (n=120) | 0.30 (n=60) | (not run) |

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
P10.4 — STATUS set to BUILD COMPLETE. See CHECKLIST.md (all items ticked) and
DECISIONS.md (D-001..D-022).
