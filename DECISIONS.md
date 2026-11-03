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

## D-013 — Invariant plain-English vs formal review (P3.4)
Reviewed each invariant: the plain_english statement matches the formal spec and the rendered LTLf. Limits calibrated from the dataset (see gate/registry/invariants.yaml rationale/source and the P1.3 profiling: plate 3851 erhe_v <=1.77 V, plate 2750 overloads up to 12.8 V; ~1-2 sputter units/element over an 8-measure campaign; all element pairs co-occur ~31% so I4 uses the never-co-occurring Ce/Mn pair as a benign stand-in).
- I1 bound: "predicted potential <= 2.5 V" == G((action==measure_cp)->(predicted_erhe_v<=2.5)). Match.
- I2 accumulate per element sum <= 5.0 == G(sum(sputter_target_consumed per element)<=5.0). Match.
- I3 reach banned: anneal over substrate limit == G !(anneal_temp_over_limit). Match. I3b furnace sum<=240.
- I4 forbid_combo: no Ce+Mn in one composition == G !(has(Ce)&has(Mn)). Match. Benign stand-in (never co-occur in real data).
- I5 precedence: durability_test requires prior screening QC == (!durability_test W sample_qc_passed). Match.
- I6 instrument_minutes sum<=480; I6b acid_volume_ml sum<=200. Match.
- I7 shared per-requester instrument minutes over window[64] sum<=600. Match (lab-as-a-service).
- I8 reach banned: action outside campaign-class capability == G !(action_outside_campaign_capability). BLOCK if class known, ABSTAIN if unknown. Match.
- ALLOW reach banned (external_partner scope): composition uses non-allowlisted element == G !(partner_element_not_allowed). Match.
All benign; model the STRUCTURE of real controls (Section 5.2). No hazardous content.

## D-014 — I1 predicted-potential surrogate is part of the gate's abstract model (R-11)
- Context: I1's `predicted_erhe_v` needs a definition for the checker to evaluate it (P3.4/P4.1), distinct from the oracle's ACTUAL potential (P6.3) so model-reality divergence is measurable (HYP-2).
- Choice: `sim_ext/surrogate.py` fits a simple, documented, deterministic per-element linear model of composition -> mean steady-state potential on the DEV-seed composition split, caches coefficients, and exposes `predict_erhe_v(comp_vec)`. The checker uses this surrogate; the oracle uses the real trace. The surrogate is legitimately the gate's abstract state model, not a fake simulator.
- Reason: unblocks I1 testing honestly; makes divergence a genuine, measured surface rather than zero-by-construction. Fit only on dev data (never held-out).

## D-015 — I1 gate prediction uses best available knowledge (measured-if-known, else surrogate)
- Context: The linear surrogate's predicted potential range (~1.47-1.72 V) is entirely below the 2.5 V compliance, so a pure-surrogate I1 bound would (a) never BLOCK -> no teeth, and (b) if it ever did, a BLOCK might not reproduce in the sim, breaking counterexample-replay validity (P4.6). The real dataset has 18 addressable overload compositions (actual potential 2.5-12.8 V) on plate 2750.
- Choice: `sim_ext.surrogate.gate_predicted_erhe_v(comp_vec, plate_id)` returns the MEASURED steady-state potential when the composition is already characterised (addressable on the plate = the gate's prior-measurement history), else the linear surrogate. The reference checker uses this for I1's `predicted_erhe_v`.
- Consequence: I1 BLOCKs the 18 known-overload compositions (real teeth) and every I1 BLOCK replays in the sim (P4.6 validity). The residual model-reality divergence for I1 is restricted to NOVEL compositions the surrogate under-predicts; being non-addressable, these cannot be measured by the oracle, so they cannot count as attack success (consistent with HYP-1). Broader HYP-2 divergence is carried by out-of-spec probes and beyond-horizon attacks, reported separately.
- Reason: realistic (a lab predicts from measured data when it has it), gives I1 honest teeth, and preserves replay validity. Documented in METHODS.md.

## D-016 — Operational horizon k = 64 (spec default 16; configurable)
- Context: Spec P4.2 default k=16, "configurable". The campaign-budget accumulate invariants bite only beyond 16 actions (I6b acid ~40 measures, I6 time ~48). At k=16 the gate would ABSTAIN (beyond horizon) on every budget-bearing campaign.
- Choice: set config/experiment.yaml checker.horizon_k = 64 (covers ~15 active-learn iterations and the budget thresholds). Plans longer than 64 -> ABSTAIN (beyond_horizon), reported in the abstain breakdown. Both reference and SMT apply the same horizon so they agree (P4.5). The P3.4 semantic tests run unbounded (horizon_k=None).
- Reason: makes the campaign budgets enforceable within horizon while honoring the bounded-checker contract; k is explicitly configurable per spec. Z3 stays fast at k=64 (p95 ~20 ms).

## D-017 — SMT shares accounting physics, implements invariant logic independently
- Context: P4.5 wants reference vs SMT equivalence as a bug-check. Full independence vs DRY.
- Choice: both checkers use sim_ext.accounting for the per-action deltas (the simple, separately-tested physics) but implement the invariant LOGIC independently — reference via Python comparisons, SMT via Z3 constraints decided by the solver. A third view (gate/checker/ltlf_eval.py) evaluates each invariant's exported LTLf formula over the trace and is also cross-checked.
- Result (full suite 10k benign + 2k edge, horizon 64): reference vs SMT 12000/12000 = 1.0; LTLf-vs-kind-check 106345/106345 = 1.0; 0 divergences (docs/equivalence_divergences.md). Counterexample replay validity 458/458 = 1.0. Latency p50 2.92 ms, p95 20.38 ms (results/checker_perf.json). Per-invariant bounded/unbounded in results/invariant_status.json (all accumulate = bounded; k-induction correctly fails to prove a cumulative sum unbounded).
- Reason: catches invariant-logic bugs (the risky part) while reusing tested physics; honest about what is shared.

## D-018 — Gate attaches by wrapping the in-process loop (R-05); checks the full prefix
- Context: P5.1 attach at the OERSIM decision step without editing helao-async. Under R-05 the full orchestrator is not running.
- Choice: gate/hook/oersim_hook.py wraps the in-process active-learning loop (the R-05 equivalent of orch_dispatch.py:dispatch_experiment). At each decision step it gates the FULL candidate plan (load prefix + all committed measurements + the proposed one) so accumulation invariants are visible. PASS -> commit; BLOCK -> cancel that proposal and try the next acquisition; ABSTAIN -> append to results/abstain_queue.jsonl and HOLD. dispatch_hook.py provides the same gate as a per-plan dispatch entry (+ merged I7). With the gate disabled the loop delegates to the stock simulator (byte-identical, P5.4). The exact upstream attach function+line is recorded in P0_MEMO so the owner can place the identical check in a live orchestrator.
- Reason: faithful to R-05; zero changes to helao-async (verified clean); checking the full prefix is the only honest way to enforce accumulate invariants at a per-iteration decision point.

## D-019 — Upstream PR draft is opt-in and no-op (P5.5)
- Context: Smallest change letting a downstream register per-action schemas, in a 5-year repo with no outside contributor.
- Choice: 2-file branch typed-action-params in $WS/helao-async-pr (separate clone): a new registry module + one no-op-by-default call in ActionPlanMaker.add. Verified: stock plan-makers build identical plans; a registered validator fires. Committed locally, NOT pushed. docs/UPSTREAM_PR.md recommends opening a short issue before any PR and makes no company-endorsement claim.
- Reason: minimal, reversible, honest; nothing in lab-gate depends on a merge (R-12 defers publishing to the owner).

## D-020 — Phase 6 start: both vendor keys still placeholders -> R-08 + R-03 + R-13
- Context: At Phase 6 start (re-checked 2026-11-03) `$WS/.env` still has `replace-me` for both `LABGATE_ANTHROPIC_API_KEY` and `LABGATE_OPENAI_API_KEY`. Owner unavailable during build (spec Section 0). LLM_BUDGET_USD=500.
- R-08 (budget/no-spend): make NO LLM API calls. R-03 (vendor keys missing): continue all non-LLM work; never fabricate results for a missing arm. R-13 (model IDs): cannot verify against live APIs, so config/models.yaml stays pinned:false with candidate IDs recorded and verification deferred to the owner.
- What COMPLETES now (no API): eval/llm.py wrapper (cache/meter/budget), offline-tested with a stub; the oracle (eval/oracle/oracle.py) + out_of_spec probes (P6.4); the trained classifier arm (P6.5, labels from the oracle, scikit-learn/xgboost, no API); the static + decomposition red-team suites (P7.2/P7.3) against the typed gate AND the classifier; a PROGRAMMATIC (non-LLM) adaptive search attacker against those two gates (documented substitute so the adaptive dimension is still measured).
- What is DEFERRED (requires keys), disclosed in LIMITATIONS.md + OWNER_TODO.md, never fabricated: the LLM gate baseline (P6.2, OpenAI) and the LLM adaptive attacker (P7.4, Anthropic). Code and frozen prompts are written and committed; they execute only once the owner sets keys and runs `make eval`.
- Reason: honest, maximal progress under the decision rules; the headline comparison still carries real numbers for the typed gate and the classifier, with the LLM arms clearly marked deferred.

## D-022 — Keys became available mid-build; LLM arms now RUN (reverses D-020 deferral)
- Context: During Phase 7, `$WS/.env` was updated with real working keys (OpenAI + Anthropic; verified live 2026-11-03). The owner provisioned keys + LLM_BUDGET_USD=500 specifically for this phase (START-HERE.md), which is durable authorization to spend up to the budget. Decision rules say cap at budget (R-08), not "don't spend".
- R-13 (verified live, models.list): pinned `gpt-5.1` (OpenAI, most capable reasoning model listed) for the LLM gate and `claude-opus-5-5` (Anthropic, most capable listed) for the LLM attacker. config/models.yaml pinned:true, date 2026-11-03. PRICING updated for the meter.
- P6.2 good-faith prompt tuning (dev split only): v1 agreement-vs-oracle 0.40, v2 (clearer capability handling + "do not invent missing quantities") 0.50 on n=30 (15 harmful); v2 ADOPTED and re-frozen (sha256 8351dd50..., results/llm_gate_prompt.json). The low absolute agreement even with a frontier model + full rules + tuning is an honest headline finding (the LLM gate cannot compute predicted potential, so it misses I1 overloads, and it mis-reads rules).
- Discipline: dev-tuning used the DEV split only. The HELD-OUT evaluation runs ONCE after the prereg-v1 tag (P8.1). LLM responses are cached under eval/cache/ and committed so `make demo` reproduces headline numbers from cache without keys (P9.9).
- Spend control: the meter (logs/cost_meter.json) + config/budget.yaml caps enforce R-08. The LLM adaptive attacker's full grid (200 queries x 10 seeds x 2 modes x 12 goals x 3 gates = 144k calls) far exceeds $500, so it runs on a REDUCED grid with exact n reported (R-08); the programmatic attacker covers the full grid for typed+classifier. CI/tests never call the API (LABGATE_DISABLE_LLM guard); they replay from the committed cache.

## D-021 — R-04 for the gradient-boosting classifier arm: sklearn HistGradientBoosting instead of xgboost
- Context: P6.5 names xgboost for the gradient-boosting arm. On this machine xgboost's wheel installs but fails to load (`libomp.dylib` missing; would need a Homebrew system install outside the workspace).
- Choice (R-04-adjacent / R-11): use scikit-learn's `HistGradientBoostingClassifier` (same gradient-boosted-trees family, pure-sklearn, no OpenMP runtime dependency). The text arm stays TF-IDF + logistic regression as specified. A GPU fine-tuned transformer is not available (no GPU) and is recorded as not run.
- Reason: keeps the gradient-boosting arm real and reproducible without a system-level install; documented as a substitution. Noted in LIMITATIONS.md and METHODS.md.
