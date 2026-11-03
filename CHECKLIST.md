# CHECKLIST

Every acceptance criterion from BUILD-SPEC.md. Tick `[x]` only when its test passes.
Mark `[FAILED, disclosed]` if R-09 applies (recorded in DECISIONS.md and LIMITATIONS.md).

## Phase 0 — Read and confirm
- [x] P0 a: P0_MEMO.md names the exact attach point with file and function. (orch_dispatch.py:1081-1124 dispatch_experiment/staged_acts; orch_host.py:564 insert_experiment)
- [x] P0 b: P0_MEMO.md lists every OERSIM action type with parameters. (10 types: 4 CPSIM + 6 GPSIM)
- [x] P0 c: Native-vs-accounting state table complete.

## Phase 1 — Environment and repo skeleton
- [x] P1 a: `make sim` runs a full OERSIM closed loop twice with the same seed and produces byte-identical trace files. (sha256 match; test_sim_deterministic.py)
- [x] P1 b: Accounting state readable at every step for every quantity the invariants need. (per-step snapshot; test_sim_deterministic.py)
- [x] P1 c: `make ci` exists and runs (lint, tests, secret scan). (ci green)

## Phase 2 — Typed boundary
- [ ] P2 a: 100% of OERSIM action types have schemas.
- [ ] P2 b: Taint test passes on 1,000 plans.
- [ ] P2 c: Static no-reference check passes.
- [ ] P2 d: Unknown-key and unit-mismatch rejection tests pass.

## Phase 3 — Policy registry and invariant language
- [ ] P3 a: Registry validates against schema; hash stable across runs.
- [ ] P3 b: All per-invariant positive and negative tests pass.

## Phase 4 — Plan checker
- [ ] P4 a: Reference vs SMT verdict equivalence = 1.0 on the full suite.
- [ ] P4 b: Counterexample replay validity = 1.0.
- [ ] P4 c: Horizon and bounded-vs-unbounded status recorded per invariant.
- [ ] P4 d: p95 latency recorded.

## Phase 5 — Attach point and packaging
- [ ] P5 a: Gate runs inside the OERSIM loop with zero changes to helao-async.
- [ ] P5 b: Gate-disabled byte-identity test passes.
- [ ] P5 c: Every verdict produces a receipt.

## Phase 6 — Baselines and oracle
- [ ] P6 a: Every LLM call cached and metered; cache hit on rerun.
- [ ] P6 b: LLM gate prompt frozen with hash before held-out runs.
- [ ] P6 c: Oracle evaluates actual simulator traces.
- [ ] P6 d: Classifier trained, dev-tuned, frozen before held-out runs.

## Phase 7 — Red team
- [ ] P7 a: All three gates face the identical static and decomposition suites.
- [ ] P7 b: Adaptive runs complete for all gates, goals, seeds, modes (or R-08 partial, reported with exact n).
- [ ] P7 c: Any attempt can be replayed from its log entry.

## Phase 8 — Preregistration and measurement
- [ ] P8 a: `prereg-v1` tag precedes the first held-out run commit.
- [ ] P8 b: All metrics computed with CIs and stored in the registry.
- [ ] P8 c: Numbers-lock CI check passes.

## Phase 9 — Packaging
- [ ] P9 a: Clean clone + `make demo` reproduces headline numbers exactly from cache, without API keys.
- [ ] P9 b: Site renders from registry data only; no external network calls at runtime.
- [ ] P9 c: Media exists (cast always; gif/webm or disclosed R-02 deferral); each under 2 minutes.
- [ ] P9 d: All docs exist; numbers-lock CI passes on them.

## Phase 10 / Final acceptance (Section 11)
- [ ] F a: `make ci` green (lint, tests, taint, static no-reference, secret scan, numbers-lock).
- [ ] F b: Reference vs SMT equivalence 1.0; counterexample replay validity 1.0.
- [ ] F c: Gate-disabled byte-identity with stock OERSIM.
- [ ] F d: Prereg tag precedes held-out runs.
- [ ] F e: All metrics with CIs in the locked registry.
- [ ] F f: Clean-clone `make demo` reproduces headline numbers from cache without keys.
- [ ] F g: Site, media, README, POST, FINAL_REPORT, HUMAN_CHECKPOINTS, AGREEMENT_PROTOCOL, LIMITATIONS, NOTICE present.
- [ ] F h: No file outside allowed dirs created or modified.
- [ ] F i: No push, no publish, no secrets in repo or history.
- [ ] F j: OWNER_TODO.md complete.
- [ ] F k: Every Section 5 content rule holds (grep for forbidden claims).
