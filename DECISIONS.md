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
