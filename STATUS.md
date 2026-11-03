# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native; `/work/BUILD-SPEC.md` absent).

## Current position
- Phase: 8 (Preregistration and measurement) — starting. CRITICAL ORDER: write PREREGISTRATION.md + git tag prereg-v1 BEFORE any held-out run (P8.1).
- Current task: P8.1 (docs/PREREGISTRATION.md + tag prereg-v1), then P8.2 held-out run ONCE, P8.3 metrics.py (+CIs), P8.4 registry.json + NUMBERS_LOCK.
- Last completed task: Phase 7 COMPLETE (code). P7.1 benign.py; P7.2 static.py; P7.3 decomposition.py + P7.3b cross_requester; P7.4 adaptive.py (programmatic; LLM attacker code present); P7.5 runner.py replayable logs. KEYS NOW LIVE (D-022): gpt-5.1 + claude-opus-5-5 pinned, LLM gate prompt v2 frozen (dev-tuned). All P7 ticked. make ci green, 72 tests. Spend so far $0.17/500.
- Next task: P8.1 prereg + tag -> P8.2 run held-out ONCE (typed+classifier full; LLM gate on held-out suites+benign sample+variance; LLM attacker reduced grid; all cached) -> P8.3 metrics+CIs -> P8.4 registry.json+NUMBERS_LOCK + numbers-lock CI

## IMPORTANT (D-022): keys live, LLM arms RUN. CI/tests guarded by LABGATE_DISABLE_LLM=1 (never call API). Held-out LLM responses cached under eval/cache/ and committed so make demo reproduces without keys. Meter enforces $500 cap. Dev-tuning already done on DEV split only; held-out is computed once after prereg-v1 tag.

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
