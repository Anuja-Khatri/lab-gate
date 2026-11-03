# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native; `/work/BUILD-SPEC.md` absent).

## Current position
- Phase: 7 (Red team) — starting
- Current task: P7.1 (streams/benign.py full stream — basic version exists, expand to 5000+5000+surprise) then P7.2 static, P7.3 decomposition, P7.4 adaptive (programmatic; LLM attacker deferred)
- Last completed task: Phase 6 COMPLETE. P6.1 eval/llm.py (cache/meter/budget, offline-tested); P6.2 llm_gate.py (frozen prompt, DEFERRED execution D-020); P6.3 oracle.py + P6.4 out_of_spec.yaml; P6.5 classifier.py (20k, HistGB+TFIDF, R-04/D-021); P6.6 splits (disjoint seed pools). All P6 ticked. make ci green, 65 tests.
- Next task: P7.1 benign stream (realistic+random+surprise, label false-block/abstain) -> P7.2 static.py (smuggling/unit/comment/bound/capability) -> P7.3 decomposition.py (+P7.3b cross-requester) -> P7.4 adaptive.py (programmatic search attacker vs typed gate + classifier; LLM attacker DEFERRED D-020) -> P7.5 replayable logs

## D-020 reminder (LLM arms): both $WS/.env keys empty/placeholder; LLM gate (P6.2) + LLM attacker (P7.4) DEFERRED, code+prompt frozen, disclosed in OWNER_TODO/LIMITATIONS. Classifier + typed gate carry real numbers. Never fabricate.

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
