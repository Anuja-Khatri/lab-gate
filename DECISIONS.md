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
