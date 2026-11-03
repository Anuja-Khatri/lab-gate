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

Headline held-out results (full table with n and 95% CIs in `docs/tables/results.md`;
every number locked in `results/registry.json`, sha256 67c0a1da):

| | typed gate | classifier | LLM gate (gpt-5.1) |
|---|---|---|---|
| attack success, static+decomp | 0.00 | 0.24 | 0.11 |
| attack success, adaptive | 0.00 | 0.33 | 0.46 |
| false-block, benign (n=13627) | 0.00 | 0.07 | 0.64 |
| false-block, surprise (n=990) | 0.00 | 0.00 | — |
| run-to-run variance | 0.00 | 0.00 | 0.30 |

Checker guarantees: reference vs SMT equivalence 1.0 (n=12000); counterexample replay
validity 1.0 (n=458); taint test 0 (no text channel, n=1000); p95 latency ~20 ms.
Specification coverage: 20.6% of attack plans reached an out-of-spec harm the gate was
never given (reported separately). Metered LLM spend: $4.44 of the $500 cap.

Hypotheses: HYP-1 supported (typed gate 0.00 on in-spec attacks); HYP-2 supported in
direction; HYP-3 supported (LLM gate nonzero attack success + 0.30 variance); HYP-4
supported (classifier degrades under adaptive attack); HYP-5 NOT supported (the typed
gate abstained 0.00 on the benign stream; the LLM gate's cost was over-blocking, not
the typed gate over-abstaining) — reported as observed.

## Disclosed deviations and decision-rule uses

- R-05: full orchestration group not launchable here; OERSIM driven in-process with
  the real action models and dataset (D-009).
- R-06: benign accounting extension for quantities OERSIM does not track (D-006).
- R-04: sklearn HistGradientBoosting instead of xgboost (libomp unavailable) (D-021).
- R-13: models verified live and pinned (gpt-5.1, claude-opus-5-5) (D-022).
- R-08: paid LLM arms ran at reduced sizes under the budget cap; deterministic adaptive
  grid reduced for compute time; all deviations and exact n in FINAL_REPORT Section 6.
- R-02: media gif/webm renderers (agg, Playwright) not installable; the asciinema cast
  is produced, gif/webm deferred to the owner (OWNER_TODO).
- No FAILED (R-09) acceptance tests.

## No-failure disclosures

- helao-async and refs clones verified unmodified; writes confined to `lab-gate/`,
  `logs/`, and `helao-async-pr/` (the never-pushed upstream draft).
- No git push, no remotes created, no publishing. Publishing is the owner's job.
- `.env` contents never printed, logged, or committed.

## Last completed task
P10.4 — STATUS set to BUILD COMPLETE. See CHECKLIST.md (all items ticked) and
DECISIONS.md (D-001..D-022).
