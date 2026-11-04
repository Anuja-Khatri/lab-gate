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

## D-023 — Owner review round 2: full-size re-run + information-parity LLM arm + extensions
- Context: Independent verification asked (1) full preregistered sizes for every adaptive/LLM arm, (2) a second information-parity LLM-gate arm given the same `gate_predicted_erhe_v` values the typed gate's I1 uses, (3) the LLM gate on a surprise-subset sample, (4) abstain breakdown by reason + an evidenced METHODS sentence on the classifier benign-vs-surprise false-block gap, (5) one-page table with per-cell n and classifier-surprise shown as 0.002, (6) re-lock + regenerate everything.
- Choices (all logged, per-role budget caps in config/budget.yaml still enforced by the meter, R-08):
  - Deterministic adaptive attacker (typed + classifier) restored to the full original spec: 200 queries x 10 seeds x 2 modes (free; CPU only).
  - adaptive-vs-LLM at 40 queries x 3 seeds x gray-box x all goals, run for BOTH LLM-gate arms (primary and parity) so the side-by-side includes adaptive.
  - Anthropic claude-opus-5-5 attacker at 6 goals x 2 seeds x 20 queries, gray-box, targeting BOTH the typed gate AND the LLM gate (item 1 "including the LLM gate").
  - variance: 120 plans x 5 repeats for both LLM-gate arms (distinct replicate tags = real calls).
  - LLM-gate benign false-block on 300 oracle-safe plans and surprise false-block on a 300-plan surprise sample, for both arms (item 3 makes the dash a number).
  - Information-parity arm (`llm_parity`): the plan JSON appended with `predicted_erhe_v` per composition-bearing action = exactly the value the typed gate's I1 uses (D-015). Its prompt is the v2 prompt plus one line explaining that field; dev-tuned on the DEV split only, frozen+hashed (results/llm_gate_parity_prompt.json) before its held-out run. Reported side by side with the primary LLM gate.
  - abstain breakdown: `abstain_breakdown.typed` dict metric {reason: count} over the benign stream + static/decomposition suites (reasons: out_of_schema_action, schema_invalid, provenance_invalid, beyond_horizon, unknown_campaign_class, unknown_substrate, solver_timeout, reference_smt_disagree).
- Reason: completes/extends the preregistration exactly as the owner's independent review requested; the parity arm isolates whether the LLM gate's I1 deficit is informational (it cannot predict potential) or reasoning; all within the budget caps, all disclosed under Deviations as "completing/extending the prereg".

## D-024 — OpenAI credits exhausted mid-review -> R-03 vendor fallback to Anthropic for the LLM-gate arms
- Context: During the round-2 re-run, every NEW OpenAI call returns HTTP 429 "You have no credits remaining." The earlier held-out gpt-5.1 responses are cached and valid (made while credits existed); new OpenAI calls (full-size gate, the parity arm, the surprise sample, 120x5 variance) cannot run. Anthropic is funded and working (verified).
- R-08: stop new OpenAI calls; keep the cached gpt-5.1 numbers; never fabricate or extrapolate. R-03 (vendor unavailable): use the other vendor for the missing vendor's role, marking the limitation prominently.
- Choice:
  - Deterministic asks run at FULL size now (no API): adaptive attacker 200 queries x 10 seeds x 2 modes for typed + classifier; abstain breakdown by reason; one-page table fix; METHODS sentence.
  - The LLM-gate arms the owner asked to run at full size + the information-parity arm run on Anthropic **claude-opus-5-5** (R-03 fallback for the OpenAI gate role), at the full preregistered sizes (suite; benign 300; surprise 300 -> item 3 number; variance 120 x 5; adaptive-vs-LLM 40 x 3 for the primary arm; parity arm on suite+benign+surprise+variance so the side-by-side comparison holds the MODEL fixed and varies only the predicted_erhe_v information -- the cleanest possible parity test).
  - The adaptive LLM **attacker** runs on **claude-sonnet-5-5** (a different Anthropic model) so gate != attacker model is preserved; 6 goals x 2 seeds x 20 queries, gray-box, targeting the typed gate AND the Anthropic LLM gate.
  - The earlier OpenAI gpt-5.1 reduced-grid numbers (attack 0.11/0.46, benign false-block 0.64, variance 0.30) are reported as a consistent prior-vendor datapoint in FINAL_REPORT; the registry headline LLM-gate metrics now carry a caveat naming the model (claude-opus-5-5) and the R-03 fallback.
- Prominent disclosure: LIMITATIONS.md, FINAL_REPORT "Deviations", and every LLM metric's `caveats` state that the LLM gate ran on Anthropic (not the originally-pinned OpenAI gpt-5.1, which ran at reduced size before its account ran out of credits) and that gate and attacker are therefore the same vendor (mitigated by using different models). per-role budget caps (config/budget.yaml) still enforced by the meter.
- Reason: OpenAI is a hard external blocker outside the build's control; R-03+R-08 are the spec-sanctioned response; using the funded vendor delivers the owner's full-size + parity asks honestly and holds the model fixed for the cleanest parity isolation, with the vendor substitution disclosed everywhere.

## D-025 — BOTH vendors exhausted mid-round-2; R-08 finalize deterministically, carry earlier LLM-tail with caveats
- Context: The round-2 run completed the benign/surprise/abstain, abstain-breakdown, static+decomposition+cross-requester suites, and the FULL deterministic adaptive grid (200x10x2) for all four arms (typed, classifier, llm=claude-opus-5-5, llm_parity), saving the registry after each arm. It then crashed in the LLM-attacker phase: Anthropic returned HTTP 400 "You have reached your specified API usage limits. You will regain access on 2026-12-01." So Anthropic is now also blocked (monthly cap), and OpenAI was already out of credits (D-024). No further LLM calls of any kind are possible.
- What DID complete (round-2, in the registry): attack.{typed,classifier,llm,llm_parity}.static_decomp; attack.{typed,classifier,llm}.adaptive + curves (typed 0.0 n=240; classifier 0.317 n=240; opus llm 0.0 n=36); falseblock + abstain for all arms (notable: opus LLM gate ABSTAINS 0.90 of benign plans -- its failure mode is massive over-abstention, unlike gpt-5.1's over-blocking); surprise false-block (item 3 -> numbers for all arms); abstain_breakdown.typed.
- R-08 response (no fabrication, exact n):
  1. Deterministic tail computed now with NO API: variance.typed=0.0; spec_coverage (out-of-spec probes over the suite); equivalence/replay/latency/taint folded from results/checker_perf.json; llm.spend_usd from the meter ($30.08).
  2. BLOCKED LLM-tail carried forward as the real earlier measurements with explicit caveats (never recomputed/faked): variance.llm.flip_rate=0.30 (n=60) is the earlier OpenAI gpt-5.1 arm -- the opus run-to-run variance could not be measured (Anthropic limit); attack.llm_attacker_vs_typed=0.0 (n=8) is the earlier opus-attacker reduced run -- the round-2 6x2x20 + vs-LLM-gate target did not complete. Both marked blocked in caveats, LIMITATIONS, and FINAL_REPORT Deviations.
  3. The earlier OpenAI gpt-5.1 arm numbers (attack 0.108 static / 0.458 adaptive, benign false-block 0.643) are preserved as attack.llm_gpt51.* / falseblock.llm_gpt51.benign so the two model behaviors (gpt-5.1 over-blocks; opus over-abstains) are both on the record.
- Reason: both vendors are hard external blockers; R-08 mandates finishing deterministic work and reporting partial LLM results with exact n and no extrapolation. The owner's main round-2 asks (full deterministic adaptive, parity arm, surprise numbers, abstain breakdown, table fix) are all satisfied with real data; only the two LLM-tail arms are partial, disclosed.

## D-026 — Owner review round 3: no earlier Gemini instruction was ever received; add Gemini (R-03 cross-vendor restore)
- Context: The owner asked to check DECISIONS for an "earlier point-7 Gemini instruction." Searched DECISIONS.md, BUILD-SPEC.md, and CLAUDE.md: there is NO Gemini instruction anywhere in anything I received. The spec's Section 5 point 7 is the "forbidden frames" content rule, not a Gemini directive. Logged here as requested: the earlier Gemini instruction was never received by this build.
- Confirmed (2026-11-03): OpenAI still 429 (no credits, D-024); Anthropic still 400 (monthly usage limit until 2026-12-01, D-025). `LABGATE_GEMINI_API_KEY` is present in $WS/.env. Gemini is the only potentially-available vendor.
- Choice: add Gemini to eval/llm.py (provider dispatch, pricing, cached/metered, same per-role caps), verify models live and pin the most capable Gemini reasoning model (R-13 discipline). Use Gemini to (a) run an adaptive attacker vs the typed gate and any runnable gate arm -- labeled "extension, not preregistered" -- which restores cross-vendor separation lost in round 2; (b) run Gemini LLM-gate arms (plain + parity) at the preregistered gate sizes on benign/surprise/static/decomposition, dev-split tuning only, frozen+hashed before held-out. The parity comparison is reported WITHIN each vendor (opus-parity vs opus-plain; gemini-parity vs gemini-plain), never cross-vendor (item 4).
- Reason: the owner provided the key specifically for this; Gemini both fills the blocked Anthropic attacker tail with a genuinely cross-vendor attacker and gives a second independent LLM-gate vendor, strengthening the comparison. All within budget caps.
## D-028 — Round 3b: all three keys re-verified live; Gemini now usable, OpenAI/Anthropic still blocked
- Context: Owner says the Gemini key is a valid AQ-format key for the native google-genai endpoint and not to reject by format/length -- only the live check decides.
- Live generation probes (2026-11-03): OpenAI gpt-5.1 -> 429 no credits (BLOCKED); Anthropic opus-5-5 -> 400 monthly usage limit, regains 2026-12-01 (BLOCKED); Gemini key (now 53 chars, "AQ." prefix) -> authenticates (earlier "invalid key" was a since-replaced key). The old pin gemini-2.5-pro returned 404 "no longer available"; gemini-3.1-pro-preview works and returns strict JSON. Reasoning pro models require thinking_budget>0, so GEMINI_THINKING_BUDGET set to -1 (dynamic).
- R-13: pinned **gemini-3.1-pro-preview** (most capable Gemini reasoning model available; verified live 2026-11-03), pricing added for the meter.
- Choice: fill every Gemini arm for real (items 2 + the Gemini part of 3): Gemini adaptive attacker vs typed (6 goals x 2 seeds x 20) and vs the Gemini gate (same-vendor, marked); Gemini LLM-gate plain + parity on benign 300 / surprise 300 / static+decomposition suites; plus Gemini gate run-to-run variance 120 x 5 (extension, fills the blocked variance cell for the one live vendor). The Gemini attacker vs the typed gate restores cross-vendor separation (attacker=Gemini, gate=the non-LLM typed gate / the Gemini gate case is same-vendor). OpenAI gpt-5.1 tails (item 3) stay BLOCKED (429); Anthropic opus tails stay BLOCKED. Dev-split prompt tuning + freeze/hash before any Gemini held-out run. Non-preregistered arms labeled "extension".
- Reason: only the live check decides (owner's instruction); Gemini is live, so its arms are filled with real data under the budget caps; the still-blocked OpenAI/Anthropic tails stay "blocked, not measured", nothing backfilled or fabricated.

## D-029 — Gemini live but free-tier quota (25 req/model) too low; arms blocked, polluted values reset (R-08)
- Context: With the valid AQ key, Gemini authenticates and gemini-3.1-pro-preview returns strict JSON. But the account is free-tier: quota is ~25 generate-requests per model (per minute), with a low daily cap. The dev-tune (30 calls) completed (real dev agreement vs oracle 0.633, n=30, kept as a dev-split datapoint in results/llm_gate_gemini_prompt.json). The held-out run then 429'd (RESOURCE_EXHAUSTED) after ~55 more calls; ~85 real Gemini responses total.
- Problem: the gate-arm loops caught per-call errors and returned "ERROR", so they "completed" and upserted quota-polluted values (e.g. falseblock.gemini.benign=0.0 was ~270 ERROR + ~tens of real calls, NOT a real "never false-blocks" result). Keeping those would be fabrication-by-accident.
- Choice (R-08): RESET every Gemini held-out metric (attack.gemini*, falseblock.gemini*, abstain.gemini*, attack.gemini_attacker_vs_*, variance.llm_gemini) to value=null "blocked, not measured: Gemini free-tier quota exceeded (25 req/model), ~55 held-out calls succeeded before 429", with exact n. Do NOT keep the polluted numbers; do NOT backfill. The integration, live verification, pin, and dev-tuned frozen prompt remain, ready for a paid Gemini tier via `make eval` (OWNER_TODO). Added retry-with-backoff (5 attempts, exponential) to eval/llm.py for 429/5xx so a paid-tier rerun survives transient rate limits; lowered Gemini concurrency guidance.
- Net: all three vendors verified live but none has enough quota/credits to run full LLM arms now (OpenAI 0 credits; Anthropic monthly cap to 2026-12-01; Gemini free-tier 25/model). The held-out LLM-gate headline remains the round-2 Anthropic opus arm; the cross-vendor Gemini attacker/gate extension is blocked, disclosed. No fabrication; polluted values removed.

## D-030 — Round 3c item 0: ERROR audit finds the opus arm was truncation-contaminated; fix + re-run
- Context: Owner item 0 asks to audit ERRORs (score as reduced n, never verdicts), verify no completed metric is ERROR-derived, and add a CI test.
- Finding (serious): recomputing the opus LLM-gate benign arm from cache gave 270/300 UNPARSEABLE + 30 PASS. Root cause: the Anthropic path sent `max_tokens=400`, but opus-5-5 is a reasoning model that spends the budget on thinking, leaving empty/truncated text that does not parse as the strict-JSON verdict. `llm_verdict` then mapped unparseable output to ABSTAIN -- i.e. it scored an ERROR as a VERDICT. So the round-2 opus headline ("over-abstains 0.90 of benign", "adaptive attack success 0.0") is a TRUNCATION ARTIFACT, not real gate behaviour. (The gpt-5.1 arm is unaffected: the OpenAI path already used max_completion_tokens>=2048.)
- Fixes: (a) `_provider_call` Anthropic now sends an adequate output budget for claude-5 reasoning models; (b) the LLM gate request uses max_tokens=2048 (also busts the truncated opus cache so the re-run makes fresh, correct calls); (c) `llm_verdict` returns verdict "ERROR" for unparseable/empty output instead of ABSTAIN; (d) a shared reduced-n aggregator (`eval/metrics.decided_counts`) excludes ERROR/DEFERRED/CACHE_MISS from n and never maps them to a verdict; the held-out drivers use it. A CI test (tests/test_error_scoring.py) enforces this.
- Re-run (Anthropic now LIVE, item 1): the opus gate arms (benign/surprise/static+decomp, plain + parity) are RE-RUN with the fix; the contaminated round-2 opus metrics are reset and recomputed with reduced-n discipline. The preregistered Anthropic adaptive attacker (vs typed; vs the opus gate, same-vendor marked) and the opus variance tail (120x5) are run to completion. Within per-role caps + the $170.45 promo credit (expires 2026-11-21).
- Reason: the ERROR audit did its job -- it caught an artifact masquerading as a headline result. Correcting it with a real re-run (now that the vendor is live) is the honest fix; nothing is backfilled or fabricated.

## D-031 — Round 3c items 1-3 outcome + hard-capped Gemini attempt
- Item 1 (Anthropic preregistered arms, PRIORITY): Anthropic was live (promo credit). The opus LLM-gate arms RE-RAN to completion with the fixed token budget + reduced-n (benign/surprise/static+decomp, plain + parity; n_errors=0) -> the real opus gate is PERMISSIVE: benign false-block 0.003, abstain 0.003 (decided coverage ~0.99), static+decomp attack success 0.278; information parity (within-vendor) drops attack success to 0.029. The programmatic attacker vs the fixed opus gate got PARTIAL n=16 (cap hit mid-phase). The PREREGISTERED Anthropic adaptive attacker (6x2x20) then hit the Anthropic monthly usage cap again (400, regains 2026-12-01) and did NOT complete: attack.llm_attacker_vs_typed stays the earlier real reduced n=8; attack.llm_attacker_vs_llm and the opus variance tail are "blocked, not measured" (no backfill). All within caps; ~$30 new Anthropic spend of the promo credit.
- Item 2 (OpenAI gpt-5.1 tails): OpenAI still 429 (no credits) -> stays blocked, not measured.
- Item 3 (Gemini): attempted the SMALLEST useful arm (Gemini attacker vs typed, 2 goals x 1 seed x 10 queries, EXTENSION + reduced) under a HARD $1.50 spend guard; result recorded by the guarded run (filled if quota allowed under the cap, else stays "blocked, not measured"). See attack.gemini_attacker_vs_typed caveat.
- Reason: item 0's audit forced the opus re-run, which overturned the round-2 artifact (opus over-abstains) with the real finding (opus is permissive; parity helps). Remaining LLM tails are blocked by hard vendor limits, reported with exact n, nothing backfilled or fabricated.

## D-032 — Round 3d: free re-scoring pass + preregistered Anthropic run (live)
- Item 0 (free re-scoring, no API): re-scored every cached LLM gate response with the corrected parser (unparseable/empty -> ERROR, reduced n). Per-arm truncation rates: gpt-5.1 benign 0.000, gpt-5.1 variance repeats 0.000 (gpt-5.1 CLEAN -> all its metrics unchanged: false-block 0.643, static+decomp 0.108, adaptive 0.458, variance 0.30 all stand); opus PRE-FIX benign 0.900 (the artifact); opus POST-FIX benign 0.000 (fix verified). Only the pre-fix opus arms were contaminated and were already corrected in 3c. Documented old->new in docs/CORRECTIONS.md (never silent). Added abstain.llm_gpt51.benign=0.010 (real, from re-scoring; previously unstored).
- Item 1: Anthropic re-verified LIVE (the monthly cap had reset / promo credit usable). Re-ran eval.heldout_anthropic to run the PREREGISTERED arms to completion before the 2026-11-21 promo expiry: the opus gate arms (cached, fast), the programmatic attacker vs the opus gate, the preregistered Anthropic adaptive attacker (6x2x20) vs the typed gate and vs the opus gate (SAME-VENDOR marked), and the opus run-to-run variance (120x5). Reduced-n discipline throughout; registry saved per arm. Any arm still unfinished if the cap re-hits stays "blocked, not measured" (exact n, no backfill).
- Item 2: blocked stays blocked (OpenAI no credits; anything the cap re-blocks), frozen prompts, caps apply. Re-lock + regenerate + ci + demo + docs follow.
- Reason: item 0 was a free integrity check that confirmed gpt-5.1 clean and bounded the damage to the (already-fixed) opus pre-fix runs; item 1 uses the live window to complete the preregistered Anthropic arms.

## (superseded) earlier Gemini-invalid note
- UPDATE (verified live 2026-11-03): the provided `LABGATE_GEMINI_API_KEY` is INVALID (Google API returns 400 "API key not valid"; the value is 24 chars, a real AI Studio key is ~39 chars "AIza..."). So Gemini cannot run either; with OpenAI and Anthropic also blocked, NO vendor is currently usable. Per R-08/R-03: the Gemini integration and live model-verification code are added to eval/llm.py so a valid key + `make eval` runs them later; but every Gemini arm (attacker, plain gate, parity gate) is recorded "blocked, not measured: invalid Gemini key" with n=0, never fabricated or backfilled. The intended cross-vendor LLM-attacker-vs-LLM-gate comparison therefore remains unmeasured; disclosed in LIMITATIONS and FINAL_REPORT. No dev-split Gemini prompt tuning was possible (it needs live calls), so no Gemini prompt was frozen; the integration would reuse the vendor-agnostic frozen prompt text.

## D-027 — Round-3 registry hygiene (items 4,5,6,7)
- item 7 (no backfill): the round-2 `variance.llm.flip_rate`=0.30 was the OpenAI gpt-5.1 value used as a stand-in for the (blocked) opus variance. That is a backfill. REMOVE it; record the opus run-to-run variance as "blocked, not measured" (metric `variance.llm_opus.flip_rate`, value null, n=0, caveat); keep the real gpt-5.1 measurement as `variance.llm_gpt51.flip_rate`=0.30 (n=60) and the new Gemini variance as `variance.llm_gemini.flip_rate`.
- item 5: add an abstain (= 1 - decided-coverage) row per gate arm to the one-page headline table and FINAL_REPORT, so a 0.00 false-block from a 0.90-abstaining gate is never unqualified.
- item 6: every metric where the gate and the attacker are the SAME vendor carries an explicit same-vendor caveat (e.g. the Gemini-attacker-vs-Gemini-gate number); where they differ (Gemini attacker vs typed gate, which is not an LLM) no such caveat.
- item 4: parity effect only ever compared within one vendor.

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
