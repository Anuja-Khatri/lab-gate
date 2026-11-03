# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native; `/work/BUILD-SPEC.md` absent).

## Current position
- Phase: 5 (Attach point and packaging as a plugin) — starting
- Current task: P5.1 (gate/hook/oersim_hook.py)
- Last completed task: Phase 4 COMPLETE. P4.1 reference.py; P4.2 smt.py (Z3, k-induction); P4.3 verdict.decide (reference+SMT, disagree->ABSTAIN); P4.4 certificates.py; P4.5 equivalence.py (FULL 12k = 1.0, LTLf 1.0); P4.6 oracle.py replay (458/458=1.0); P4.7 latency (p50 2.92/p95 20.38 ms). All P4 ticked. make ci green, 52 tests.
- Next task: P5.1 oersim_hook.py (attach at decision step; PASS/BLOCK/ABSTAIN routing + abstain_queue.jsonl) -> P5.2 dispatch_hook.py -> P5.3 receipts.py -> P5.4 gate-disabled byte-identity test -> P5.5 helao-async-pr draft (no push) + docs/UPSTREAM_PR.md

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
