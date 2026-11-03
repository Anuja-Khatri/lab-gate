# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native; `/work/BUILD-SPEC.md` absent).

## Current position
- Phase: 4 (Plan checker) — in progress; reference.py (P4.1) already built in Phase 3 to enable P3.4
- Current task: P4.2 (SMT encoding in gate/checker/smt.py)
- Last completed task: Phase 3 COMPLETE. P3.1 schema.py (4 kinds) + ltlf.py (Dwyer patterns); P3.2 invariants.yaml (I1-I8, I3b, I6b, ALLOW; dataset-calibrated; I7 fixed to joint-shared window=200); P3.3 lock.py (sha256). P3.4 per-invariant pos/neg tests via gate/checker/reference.py (P4.1 done early) + sim_ext/surrogate.py (D-014/D-015). All P3 acceptance ticked. make ci green, 44 tests.
- Next task: P4.2 smt.py (Z3 bounded LTLf) -> P4.3 verdict wiring -> P4.4 certificates.py -> P4.5 equivalence.py (10k+2k suite) -> P4.6 counterexample replay -> P4.7 latency

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
