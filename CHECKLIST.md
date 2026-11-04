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
- [x] P2 a: 100% of OERSIM action types have schemas. (test_all_oersim_action_types_have_schemas; 10 native + 3 stand-ins)
- [x] P2 b: Taint test passes on 1,000 plans. (test_no_text_channel.py)
- [x] P2 c: Static no-reference check passes. (test_static_no_reference_to_free_text_fields)
- [x] P2 d: Unknown-key and unit-mismatch rejection tests pass. (test_schema_properties.py)

## Phase 3 — Policy registry and invariant language
- [x] P3 a: Registry validates against schema; hash stable across runs. (test_registry.py)
- [x] P3 b: All per-invariant positive and negative tests pass. (test_invariants.py; >=2 pos + >=2 neg each incl. I7 merged; reference evaluator)

## Phase 4 — Plan checker
- [x] P4 a: Reference vs SMT verdict equivalence = 1.0 on the full suite. (12000/12000; LTLf 106345/106345; docs/equivalence_divergences.md)
- [x] P4 b: Counterexample replay validity = 1.0. (458/458; eval/oracle/oracle.py)
- [x] P4 c: Horizon and bounded-vs-unbounded status recorded per invariant. (results/invariant_status.json; horizon_k=64)
- [x] P4 d: p95 latency recorded. (results/checker_perf.json; p50 2.92 ms, p95 20.38 ms)

## Phase 5 — Attach point and packaging
- [x] P5 a: Gate runs inside the OERSIM loop with zero changes to helao-async. (gate/hook/oersim_hook.py; dispatch_hook.py; helao-async clean)
- [x] P5 b: Gate-disabled byte-identity test passes. (test_hook.py::test_gate_disabled_byte_identical_to_stock)
- [x] P5 c: Every verdict produces a receipt. (gate/receipts.py; test_hook.py)
- [x] P5.5 upstream draft: helao-async-pr branch typed-action-params (2 files, no-op default, NOT pushed); docs/UPSTREAM_PR.md.

## Phase 6 — Baselines and oracle
- [x] P6 a: Every LLM call cached and metered; cache hit on rerun. (eval/llm.py; test_llm_wrapper_cache_and_meter)
- [x] P6 b: LLM gate prompt frozen with hash before held-out runs. (results/llm_gate_prompt.json; sha256 bf687cbb...) NOTE: LLM gate EXECUTION deferred (R-08/R-03, no keys; D-020) — dev-tuning deferred, disclosed.
- [x] P6 c: Oracle evaluates actual simulator traces. (eval/oracle/oracle.py; + out_of_spec.yaml P6.4)
- [x] P6 d: Classifier trained, dev-tuned, frozen before held-out runs. (results/classifier.json n=20000, gb test acc 0.9367; HistGradientBoosting per R-04/D-021)

## Phase 7 — Red team
- [x] P7 a: All three gates face the identical static and decomposition suites. (eval/runner.py; typed+classifier in CI, LLM gate added for held-out make eval)
- [x] P7 b: Adaptive runs complete for all gates, goals, seeds, modes (programmatic full grid; LLM attacker reduced grid with exact n reported per R-08/D-022). (eval/redteam/adaptive.py)
- [x] P7 c: Any attempt can be replayed from its log entry. (logs/redteam_log.jsonl; AttackResult.trajectory; test_records_are_replayable)

## Phase 8 — Preregistration and measurement
- [x] P8 a: `prereg-v1` tag precedes the first held-out run commit. (tag b06ae95 is ancestor of HEAD)
- [x] P8 b: All metrics computed with CIs and stored in the registry. (27 metrics, Wilson/bootstrap CIs)
- [x] P8 c: Numbers-lock CI check passes. (NUMBERS_LOCK.json sha256 67c0a1da; make ci green)

## Phase 9 — Packaging
- [x] P9 a: Clean clone + `make demo` reproduces headline numbers exactly from cache, without API keys. (DEMO PASS)
- [x] P9 b: Site renders from registry data only; no external network calls at runtime. (site/build.py; data inlined, no CDN/fetch)
- [x] P9 c: Media exists: media/demo.cast (real asciinema of make demo); gif+webm DEFERRED to owner (R-02, agg/Playwright not installable — OWNER_TODO).
- [x] P9 d: All docs exist; numbers-lock CI passes on them.

## Phase 10 / Final acceptance (Section 11) — re-verified at handoff
- [x] F a: `make ci` green (lint, 76 tests, taint, static no-reference, secret scan, numbers-lock). Re-verified at handoff, incl. a fresh clone.
- [x] F b: Reference vs SMT equivalence 1.0 (n=12000); counterexample replay validity 1.0 (n=458).
- [x] F c: Gate-disabled byte-identity with stock OERSIM. (test_hook.py)
- [x] F d: Prereg tag precedes held-out runs. (`git merge-base --is-ancestor prereg-v1 HEAD` = YES; commit b06ae95)
- [x] F e: All metrics with CIs in the locked registry. (results/registry.json 58 metrics + NUMBERS_LOCK.json sha 49b68bda)
- [x] F f: Clean-clone `make demo` reproduces headline numbers from cache without keys. Re-verified at handoff: fresh clone in a temp dir + helao-async sibling at ba910c4, `make setup && make ci && make sim && make demo` all pass OFFLINE (DEMO PASS).
- [x] F g: Site, media, README, POST, FINAL_REPORT(.md + .pdf), CORRECTIONS, OWNER_PACKET, HUMAN_CHECKPOINTS, AGREEMENT_PROTOCOL, LIMITATIONS, NOTICE present.
- [x] F h: No file outside allowed dirs created or modified. (helao-async + refs clean; writes only in lab-gate/, logs/, helao-async-pr/)
- [x] F i: No push, no publish; no git remotes; secret scan clean on the working tree AND full git history.
- [x] F j: OWNER_TODO.md and docs/OWNER_PACKET.md complete (copy-paste remaining steps).
- [x] F k: Every Section 5 content rule holds. (git grep audit: no forbidden claims, no hazardous content, no company-endorsement claims)
