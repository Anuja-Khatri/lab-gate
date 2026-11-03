# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native; `/work/BUILD-SPEC.md` absent).

## Current position
- Phase: 6 (Baselines and oracle) — starting. NOTE: LLM arms need real keys in $WS/.env (currently placeholders). Apply R-13 (model pin) / R-03 / R-08 at Phase 6 start.
- Current task: P6.1 (eval/llm.py wrapper) + re-check .env keys
- Last completed task: Phase 5 COMPLETE. P5.1 oersim_hook.py; P5.2 dispatch_hook.py; P5.3 receipts.py; P5.4 gate-disabled byte-identity; P5.5 helao-async-pr branch (no push) + docs/UPSTREAM_PR.md. helao-async verified untouched. All P5 ticked. make ci green, 59 tests.
- Next task: P6.1 eval/llm.py (cached/metered/budget, reads $WS/.env) -> P6.2 llm_gate.py (OpenAI) -> P6.3 oracle out_of_spec (oracle.py exists; add out_of_spec.yaml) -> P6.4 -> P6.5 classifier.py (xgboost+tfidf) -> P6.6 splits frozen

## KEY BLOCKER for Phase 6: $WS/.env keys are still "replace-me"
- If keys remain placeholders: build eval/llm.py + prompts + classifier (non-LLM parts) fully; the classifier arm (P6.5, oracle-labeled, no API) can complete. The LLM gate (P6.2) and adaptive attacker (P7.4) REQUIRE keys -> if absent, apply R-08 (no spend) / R-03 and DEFER those arms, disclosed in LIMITATIONS.md + OWNER_TODO.md. Never fabricate LLM-arm results.

## Checker design notes (for resume)
- reference.evaluate(parsed, registry): single-plan PASS/BLOCK/ABSTAIN over abstract trace. evaluate_merged(plans): I7 shared-window across requesters.
- I1 uses sim_ext.surrogate.gate_predicted_erhe_v (measured-if-addressable else linear surrogate) — D-015; gives I1 teeth on 18 real overloads + replay validity.
- Capability (I8) + ALLOW checked first; accumulate-with-window (I7) skipped in single-plan (merged only).
- Budgets couple: per-measure = 10 instr-min, 5 ml acid, 1.0 consumption split by fraction; durability = 60 min. SMT must mirror accounting.apply_action exactly.

## Environment quick-ref
- venv: `lab-gate/.venv` (Python 3.12). Run via Makefile (sets PYTHONPATH=$WS/helao-async:$WS/lab-gate).
- Action vocabulary (D-010): 10 OERSIM-native actions + benign stand-ins (deposit_composition, anneal, durability_test).
- Dataset: 2 plates (2750 has real overload traces up to erhe_v 12.8 V; 3851 well-behaved), 13 elements, comp_vec sums to 100.
- R-05 bypass: FastAPI/Bokeh group + GP acquisition (torch). Oracle/gate use real data.

## Preconditions (checked 2026-11-03)
1. `.env` present with `LABGATE_ANTHROPIC_API_KEY`, `LABGATE_OPENAI_API_KEY` (both placeholder `replace-me`), `LLM_BUDGET_USD=500`. Owner must set real keys before Phase 6. Non-LLM work (Phases 0-5) proceeds now.
2. `helao-async` HEAD = `ba910c4c2bdcbcbc49476e32a5b20ca0abb93529` — already equals the pin `ba910c4` (commit dated 2026-10-19). No checkout needed; helao-async stays untouched.
3. `refs/consilience-verification` present (HEAD 275dba8).
4. Docker CLI available.
5. Tooling: system Python 3.15.0, NO conda, `uv` present, `git` present. (See D-002 for env plan.)

## Blockers resolved
- none yet

## Notes
- Hard path discipline: write only in `$WS/lab-gate/`, `$WS/scratch/`, `$WS/logs/` (and `$WS/helao-async-pr/` in Phase 5). No pushes, no subagents.
