# DECISIONS

Append only. Every non-trivial decision, numbered D-001 onward: context, options, choice, reason.
Decision-rule uses (R-01..R-13) are logged here too.

---

## D-001 — Workspace detection
- Context: Spec Section 1 says detect `$WS`: if `/work/BUILD-SPEC.md` exists `$WS=/work`, else `~/lila-gate`.
- Finding: `/work/BUILD-SPEC.md` does not exist; running natively on macOS.
- Choice: `$WS = /Users/anujakhatri3/lila-gate`.
- Reason: Matches the native branch of the detection rule. Recorded in STATUS.md.

## D-002 — Python environment (R-04-adjacent, R-11)
- Context: Spec P1.2 wants a Python 3.14 conda env matching helao-async. This machine has NO conda and system Python is 3.15.0. `uv` is available.
- Options: (a) install conda/miniforge; (b) use system Python 3.15 directly; (c) use `uv venv` pinned to a Python version.
- Choice (planned, to finalize in P1.2): use `uv venv` to create the main lab-gate env. Target the Python version helao's env file pins (to be read in P0/P1); if 3.14 wheels are missing for `z3-solver`/`xgboost`/`torch`, create Python 3.12 sidecars under `lab-gate/.sidecar/` per R-04.
- Reason: `uv` is present and reproducible; installing conda system-wide is a heavier, less reversible change. Conservative + honest (R-11). Final version and any sidecars recorded when P1.2 runs.

## D-003 — helao-async pin already satisfied
- Context: Precondition 2 / spec P0 pin to commit `ba910c4`.
- Finding: fresh clone HEAD is `ba910c4c...`, which equals the pin.
- Choice: take no action on the helao-async working tree (no checkout), leaving it untouched per the hard rule.
- Reason: HEAD already matches the pin, so no modification is needed. R-01 (pin unavailable) does NOT apply; the pin is reachable.

## D-004 — API keys are placeholders at build start (pre-R-03 note)
- Context: `.env` ships with `replace-me` placeholders for both vendor keys.
- Choice: proceed with all non-LLM work (Phases 0-5) now. Defer the R-03 / R-08 determination to Phase 6 start, re-reading `.env` then. If still placeholders at Phase 6, apply R-03 (missing-vendor handling) / R-08 (no spend) and disclose; never fabricate LLM-arm results.
- Reason: Owner was told to set real keys before Phase 6; Phases 0-5 need no keys. Honest deferral.

## D-005 — Gate attach point (P0.2)
- Context: Spec P5.1 needs the exact point where a proposed OERSIM plan can be gated without editing helao-async.
- Finding: `helao/hexagon/app/orch_dispatch.py :: dispatch_experiment` (line 1081) expands an experiment into `staged_acts` (fully-typed `Action` list, globals applied) at line 1112 and appends to `action_dq` at lines 1123-1124. The decision-step requeue enters at `orch_host.py :: insert_experiment` (line 564).
- Choice: primary attach = the `staged_acts` list in `dispatch_experiment` (P5.1); secondary per-action attach = `_stage_action_for_dispatch` (orch_dispatch.py:868)/`_dispatch_action_locked` (:897) for P5.2. Implement via wrapping/injection, never editing helao-async.
- Reason: `staged_acts` is the first point where a whole proposed plan is concrete and typed. Both locations cited so the owner can place the identical check in a live orchestrator.

## D-006 — R-06 accounting quantities (P0.2)
- Context: Invariants I1-I8 need quantities OERSIM does not natively track.
- Choice: `sim_ext/accounting.py` derives sputter-target consumption (per element from comp_vec fractions), furnace time, instrument hours, acid volume, screening-QC flag, shared cross-requester instrument-hours, and carries requester/campaign-class provenance — all deterministic functions of action params. Native quantities (plate id, comp_vec/elements, overpotential eta via calc_eta, fixed current) are read directly. Full table in docs/P0_MEMO.md Section 4.
- Reason: R-06 mandates a benign accounting wrapper fed from action parameters; no helao-async edits. Units/rules documented in code and METHODS.md.

## D-007 — Reference patterns to reuse (P0.3)
- Context: Spec P0.3 says reuse PATTERNS from refs/consilience-verification, not consciousness-domain content.
- Choice: reuse taint test (no_text_channel_test.py), equivalence harness (equiv.py), LLM wrapper (llm.py), registry (registry.py), numbers lock (numbers_lock.py), secret scan (check_secrets.py). Mapping in docs/P0_MEMO.md Section 6. No domain vocabulary or data copied.
- Reason: These are exactly the mechanisms the spec requires (taint, equivalence, cached/metered LLM, numbers lock, secret scan).

## D-008 — Environment finalized (P1.2, closes D-002)
- Context: No conda; system Python 3.15; helao wants 3.14 conda env.
- Choice: `uv venv --python 3.12 lab-gate/.venv` (gitignored). Installed the deterministic core (pydantic, z3-solver, numpy, pandas, scikit-learn, pint, pyyaml, hypothesis, pytest, matplotlib, pyzstd, python-dotenv, ruff) plus the light helao import deps (aiofiles, requests, aiohttp, colorama, colorlog, ntplib, aiodebug, aioshutil, pydasher, uuid7, ruamel.yaml, orjson, fastapi, pydantic-settings) so the REAL helao action models and OERSIM plan-makers import in-process. `requirements.txt` records the set. PYTHONPATH=$WS/helao-async.
- Verified: `helao.core.models.{action,experiment,sequence,machine}` import; `OERSIM_exp.OERSIM_sub_measure_CP()` builds the real 4-action plan; `oer13_cps.pzstd` loads (2 plates, 13 elements, comp_vec sums to 100, real CP3 {t_s, erhe_v}); `calc_eta` works.
- R-04 (sidecar) status: NOT needed for the deterministic core. torch/gpytorch/xgboost/z3 all either unneeded (torch/gpytorch) or wheel-available on 3.12 (z3 installed; xgboost to be checked at Phase 6). Revisit only if a Phase 6 wheel is missing.

## D-009 — R-05 TRIGGERED: full orchestration group cannot launch; drive OERSIM in-process
- Context: Spec P1.3 says launch demo0/demo1; if the FastAPI/Bokeh group fails, fall back to driving the OERSIM experiment/sequence functions + simulated potentiostat driver directly in-process, preserving action models; document what was bypassed; do not write a fake simulator.
- Finding (probed 2026-11-03): no conda (helao setup_env.sh unavailable); `uvicorn`, `bokeh`, `torch`, `gpytorch`, `zmq`(pyzmq), `boto3` all MISSING -> `orch_host` fails to import (boto3), `gpsim_driver` fails (torch), no server can bind. The full group is not launchable here.
- Choice (R-05): drive OERSIM in-process via `sim_ext/oersim.py` using the REAL helao `Action` models and the REAL OERSIM plan-maker structure, and the REAL `oer13_cps` dataset + real `calc_eta`. Bypassed and documented: (a) the FastAPI/Bokeh servers and HTTP/ZMQ dispatch; (b) the GP surrogate acquisition (`acquire_point`/`update_model`, needs torch) — for deterministic closed-loop and benign-plan GENERATION the next composition is chosen by a seeded deterministic sampler over the plate's REAL addressable compositions, not GP-EI. The oracle never needs the GP: it executes a GIVEN plan against the real dataset. No fake simulator: compositions, CP traces and eta are the real dataset values.
- Reason: faithful to R-05; preserves action models; keeps all physics from the real dataset; isolates the single unavoidable bypass (GP policy) to plan GENERATION, not to gate/oracle correctness.

## D-010 — Action vocabulary: OERSIM-native + benign protocol stand-ins
- Context: Invariants I3 (anneal/furnace), I5 (durability-after-screening), I8 (capability exposure) presuppose lab protocol steps OERSIM does not emit natively. P2.1 requires schemas for every OERSIM action type.
- Choice: the gate's typed action vocabulary = (1) the 10 OERSIM-native actions (full schema coverage -> satisfies P2 acceptance) + (2) a small set of clearly-labeled benign lab-gate protocol stand-ins (`deposit_composition`, `anneal`, `durability_test`) that model lab structure with benign quantities. Stand-ins are marked as such in `gate/boundary/schemas.py` and METHODS.md; they are NOT helao endpoints. `measure_cp` doubles as the screening measurement.
- Reason: lets I3/I5/I8 model real control STRUCTURE (Section 5.2) while keeping native-action schema coverage honest. All benign (OER parameter world only).

## D-011 — Verdict for boundary rejections: ABSTAIN, not BLOCK (R-11)
- Context: What verdict should a plan get when it fails the typed boundary (unknown action type; unknown/extra key; type confusion; unit mismatch; out-of-physical-bounds; bad provenance)? Spec P4.3 says BLOCK requires a concrete counterexample and ABSTAIN covers "out-of-schema or novel action".
- Choice: the gate only BLOCKs when it has a concrete state-trace counterexample (a modeled policy violation, Phase 4). Anything it cannot even type -> ABSTAIN (fail closed, routed to the human queue), with distinct reasons logged: `out_of_schema_action`, `schema_invalid` (extra key / type confusion / unit mismatch / out-of-physical-bounds), `provenance_invalid`. None of these ever PASS.
- Reason: most conservative honest option. A malformed/smuggled plan is not a proven policy violation, so fabricating a BLOCK counterexample would be dishonest; refusing to certify (ABSTAIN) is correct and keeps the smuggling red-team (P7.2) from ever passing. These reasons feed the abstain-breakdown metric (P8.3). Distinct from invariant bounds (substrate temp limit, compliance), which ARE policy BLOCKs in Phase 4.

## D-012 — Decision entrypoint stable from Phase 2; checker wired in Phase 4
- Context: The taint test (P2.4) must run the real decision path now, but the reference+SMT checker is Phase 4.
- Choice: `gate/verdict.py::decide` is the stable entrypoint. Phase 2 runs the boundary and returns ABSTAIN for un-typeable plans and a provisional `TYPED_OK` marker for well-typed plans (never PASS without a proof). The verdict depends ONLY on the quarantined plan, so the taint-test invariant is inherited unchanged when Phase 4 replaces the TYPED_OK branch with the checker.
- Reason: lets P2.4 assert the no-text-channel property on the real entrypoint while being honest that no PASS is issued before a proof exists.
