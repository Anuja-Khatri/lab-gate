# OWNER_TODO

Items that require you (Anu). Claude Code cannot and will not do these. Filled in as the build proceeds; finalized in P10.3.

## Before Phase 6 (LLM evaluation)
- [ ] Replace the placeholder keys in `$WS/.env`:
  - `LABGATE_ANTHROPIC_API_KEY=` (currently `replace-me`)
  - `LABGATE_OPENAI_API_KEY=` (currently `replace-me`)
  - Keep `LLM_BUDGET_USD=500` or adjust.
  - Set a matching spend limit in each provider console as a second safety net.
  - If keys are not set when the build reaches Phase 6, the LLM-dependent arms are deferred and disclosed (R-03 / R-08); deterministic work still completes.

## DEFERRED LLM arms (keys were never set during the build — D-020)
The build ran all non-LLM work. To run the two LLM-dependent arms, set the keys in
`$WS/.env` (see top of this file) and run `make eval`:
- [ ] LLM gate baseline (OpenAI). Prompt is frozen in `results/llm_gate_prompt.json`
  (sha256 recorded). Dev-split prompt tuning was deferred (no keys); if you tune,
  log versions + dev scores in DECISIONS.md and re-freeze before the held-out run.
- [ ] LLM adaptive attacker (Anthropic). Code in `eval/redteam/adaptive.py` (the
  programmatic adaptive attacker ran; the LLM attacker needs keys).
- [ ] R-13 model IDs: `config/models.yaml` has `pinned: false` with candidate IDs
  (`gpt-5.5`, `claude-opus-5-5`). Verify against the live APIs and pin, recording
  the date, before trusting the LLM-arm numbers.
- Note (R-04/D-021): the gradient-boosting classifier uses sklearn
  HistGradientBoosting because xgboost's wheel can't load libomp here. If you want
  xgboost, `brew install libomp` then `uv pip install xgboost` and retrain.

## Later (written as phases complete)
- (to be filled in P10.3: OSF preregistration upload referencing the prereg-v1 tag
  hash, GitHub repo create + push, publish post, optional upstream PR, media
  rendering if a renderer is unavailable, any R-02/R-03/R-08/R-09 items)
