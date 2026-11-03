# OWNER_TODO

Everything Claude Code could do is done and committed locally. These items need you
(R-12: human-only — publishing, outreach, external accounts). Bring the results back
to our chat before any outreach; the notes to Guevarra, Kompa and Beam get written
after we look at the real numbers together.

## Review first
- [ ] Read `docs/FINAL_REPORT.md` and `DECISIONS.md` (D-001..D-022). The headline:
  typed gate 0.00 attack success and 0.00 benign false-block; LLM gate 0.64 benign
  false-block and 0.30 run-to-run variance; classifier 0.24/0.33 attack success.
  Spend was $4.44 of the $500 cap.
- [ ] Skim `results/registry.json` + `docs/tables/results.md` (every number, with n
  and 95% CI). Confirm you are comfortable with the reduced-run deviations listed in
  FINAL_REPORT Section 6 before anything is published.

## Publish (human-only)
- [ ] Upload `docs/PREREGISTRATION.md` to OSF, referencing the binding git tag
  `prereg-v1` (commit `b06ae95`). Disclose on OSF that the git tag is the binding
  timestamp.
- [ ] Create the GitHub repo and push. Suggested name/description include
  "helao-async" and "OERSIM" so engineers searching those terms find it, e.g.
  name `lab-gate`, description "A plan-checking safety gate for autonomous labs,
  built on helao-async and evaluated in its OERSIM simulator." Do NOT push the
  `eval/cache/` secrets? there are none (checked) — but review once more.
- [ ] Publish `docs/POST.md` (about 900 words). Optionally add the public-statement
  citations noted in the HTML comment at the end (each with a link, quoted under 15
  words, verified by you — I did not add links I could not verify).
- [ ] Consider arXiv for `docs/FINAL_REPORT.md`; it cites the OER paper
  (doi:10.1039/C8MH01641K lineage) and the HELAO orchestration paper, so citation
  alerts reach their authors on their own. Verify the Guevarra et al. venue/year
  before submission.

## Media rendering (R-02 deferral — tools not installable here)
- [x] `media/demo.cast` — real asciinema cast of `make demo` (recorded here).
- [ ] GIF from the cast (needs `agg`, not installable here):
  `agg media/demo.cast media/demo.gif`
- [ ] Site walkthrough webm (needs Playwright, not installable here): open
  `site/index.html`, then record with Playwright or any screen recorder; keep under
  2 minutes. A simple recipe: `pip install playwright && playwright install chromium`
  then a short script that loads the file and scrolls.

## Optional upstream contribution (R-12)
- [ ] `docs/UPSTREAM_PR.md` describes a 2-file, no-op-by-default seam in
  helao-async (branch `typed-action-params` in `$WS/helao-async-pr`, committed
  locally, NOT pushed). Open a short issue first; do not open a PR cold. Nothing in
  lab-gate depends on a merge.

## Keys / models (done, for your awareness)
- [x] Real OpenAI + Anthropic keys were set in `$WS/.env` and used within the $500
  cap ($4.44 spent). R-13 models pinned and verified live 2026-11-03:
  `gpt-5.1` (LLM gate), `claude-opus-5-5` (LLM attacker). See `config/models.yaml`.
- [x] R-04: the gradient-boosting classifier uses sklearn HistGradientBoosting
  (xgboost's wheel cannot load libomp here). To switch: `brew install libomp` then
  `uv pip install xgboost` and retrain. A GPU transformer text classifier was not
  run (no GPU).
- [ ] If you rerun the full-scale evaluation (the prereg sizes rather than the
  reduced grid in FINAL_REPORT Section 6), set keys and run `make eval`; the meter
  enforces the cap. Everything else reproduces offline with `make demo`.

## Reproduce (no action needed, for reference)
- `make ci` green (lint, tests, taint, static no-reference, secret scan, numbers lock).
- `make demo` reproduces the headline numbers from cache without keys.
- Docker image: `docker build -f docker/Dockerfile -t lab-gate .` then
  `docker run --rm lab-gate` runs the offline demo (build needs network to clone
  helao-async at the pin).
