# STATUS

Workspace (`$WS`): `/Users/anujakhatri3/lila-gate` (native; `/work/BUILD-SPEC.md` absent).

## Current position
- Phase: 3 (Policy registry and invariant language) — starting
- Current task: P3.1 (registry schema + LTLf renderer)
- Last completed task: Phase 2 COMPLETE. P2.1 gate/boundary/schemas.py (13 action schemas, extra=forbid, bounds, provenance, parse_plan); P2.2 units.py (pint, fail-closed); P2.3 quarantine.py; P2.4 taint test (1000 plans) + static no-reference; P2.5 hypothesis props. gate/verdict.py decision entrypoint (D-012). All 4 P2 acceptance items ticked. make ci green, 15 tests.
- Next task: P3.1 registry/schema.py + registry/ltlf.py -> P3.2 invariants.yaml (I1-I8 + allowlist) -> P3.3 lock.py -> P3.4 per-invariant pos/neg tests

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
