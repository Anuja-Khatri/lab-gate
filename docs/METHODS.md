# Methods

Plain language. This describes how lab-gate is built and evaluated. Numbers live in
results/registry.json and render into docs/tables/results.md and the site under the
numbers lock.

## Environment (R-05)

The full helao-async FastAPI/Bokeh orchestration group could not launch on the build
machine (no conda; uvicorn/bokeh/torch/ZeroMQ/boto3 absent). Per decision rule R-05
the OERSIM active-learning loop is driven in-process: lab-gate imports the real
helao-async `Action`/`Experiment`/`Sequence` models and reproduces the exact action
sequence of the `OERSIM_sub_*` experiment plan-makers (cross-checked in
tests/test_oersim_fidelity.py), and `measure_cp` replays the real stored
chronopotentiometry (CP) trace from the `oer13_cps` dataset and computes the real
overpotential via helao's `calc_eta`. The only bypass is the GP-surrogate acquisition
policy (needs torch), replaced for closed-loop simulation and benign-plan generation
by a seeded deterministic sampler over the plate's real addressable compositions. The
oracle never needs the GP: it executes a given plan against the real dataset.
helao-async is used read-only and never modified (verified clean).

## The gate

1. Typed boundary (`gate/boundary/`). One strict pydantic model per action type
   (`extra="forbid"`), bounds where physically meaningful, and pint-based unit
   normalisation that fails closed on a dimensional mismatch. Free-text fields
   (`action_comment`, `experiment_comment`, `experiment_label`, `sequence_comment`,
   `sequence_label`) are quarantined before anything downstream sees the plan; the
   stripped text is stored only in the receipt and never read by the checker. A taint
   test injects a sentinel into every free-text field of 1,000 plans and asserts the
   verdict is byte-identical and the sentinel never reaches a checker input or output;
   a static check asserts the checker/verdict modules never name those fields.

2. Registry (`gate/registry/`). Benign invariants in four kinds (bound, accumulate,
   forbid_combo, reach), each rendered as a finite-trace linear temporal logic (LTLf)
   formula with its Dwyer-Avrunin-Corbett specification-pattern name. The registry is
   canonicalised and SHA-256 hashed; every verdict and result records the hash.

3. Checker (`gate/checker/`). A pure-Python reference evaluator steps the plan through
   an abstract state trace (R-06 accounting plus native/derived variables) and
   evaluates every invariant; an independent Z3/SMT encoder does the same by bounded
   model checking to horizon k = 64, attempting k-induction for the accumulate
   invariants (recorded bounded vs unbounded). An equivalence harness runs both over
   10,000 benign + 2,000 edge plans and compares verdicts exactly. PASS requires the
   SMT to prove no violation reachable within the horizon and the reference to agree;
   BLOCK yields a concrete counterexample trace; ABSTAIN covers un-typeable plans,
   beyond-horizon, unmodeled state, unknown campaign class/substrate, and solver
   timeout. Every BLOCK counterexample is replayed in the simulator and confirmed by
   the oracle.

## R-06 accounting

`sim_ext/accounting.py` derives, deterministically from action parameters, the benign
quantities OERSIM does not natively track: per-element sputter-target consumption
(from comp_vec atomic fractions), instrument minutes, acid volume, furnace minutes,
per-sample screening-QC flags, and per-requester instrument minutes over a scheduling
window. Native quantities (loaded plate, composition/elements, overpotential via
`calc_eta`, fixed current) are read directly.

## I1 prediction (D-015)

The gate predicts a measurement's steady-state potential from its BEST available
knowledge: the measured value when the composition is already characterised
(addressable on the plate), otherwise a linear per-element surrogate fit on a dev
split (`sim_ext/surrogate.py`). This gives I1 teeth on the dataset's real overload
compositions and makes every I1 BLOCK replay in the simulator. The oracle uses the
actual measured potential; the gap between the gate's abstract model and the
simulator's real dynamics is the measurable model-reality divergence surface (HYP-2).

## Baselines

- LLM gate (`eval/baselines/llm_gate.py`): OpenAI gpt-5.1 (pinned 2026-11-03, R-13)
  given the plain-English rules and the full plan JSON including comment fields. The
  prompt was tuned in good faith on the dev split (v1 -> v2, agreement vs oracle 0.40
  -> 0.50 on n=30) and frozen with its hash before any held-out run.
- Classifier (`eval/baselines/classifier.py`): a learned safeguard. sklearn
  HistGradientBoosting on engineered plan features (D-021; xgboost's wheel could not
  load its OpenMP runtime), plus TF-IDF + logistic regression on the serialized plan
  text including comments. Trained on 20,000 oracle-labeled plans, split train/dev/test
  by disjoint generator-seed pools, threshold tuned on dev, frozen before held-out. A
  GPU fine-tuned transformer was not run (no GPU).

## Oracle and out-of-spec

The oracle (`eval/oracle/oracle.py`) executes a plan over the ACTUAL simulated trace
and flags any registry invariant violated. Four benign out-of-spec harm predicates
(`out_of_spec.yaml`, OS1-OS4) the gate is NOT given measure specification coverage:
what any rule-based gate cannot catch because it was never told. They are reported
separately and never folded into headline attack-success numbers.

## Red team

Static suite (`eval/redteam/static.py`): smuggling (extra keys, type confusion,
nested dicts), unit games, comment injection, single-step bound violations, capability
smuggling. Decomposition (`decomposition.py`): accumulation/ordering violations where
each step is individually valid, plus beyond-horizon plans; cross-requester plans that
jointly violate the shared budget (including one attacker with several identities).
Adaptive (`adaptive.py`): a programmatic search attacker (harm-preserving surface
mutations with gate feedback, full grid) and an Anthropic claude-opus-5-5 attacker
(reduced grid, R-08). Attack success = gate PASSES and the oracle observes the target
invariant violated. Every attempt is logged replayably.

## Measurement

Rates use Wilson 95% CIs; curves use bootstrap 95% CIs. The held-out evaluation runs
once after the `prereg-v1` git tag. Every number renders from results/registry.json
under the numbers lock (results/NUMBERS_LOCK.json); a CI check fails if any
result-like number in docs/ or site/ is not derivable from the registry. Deviations
from the preregistered run sizes are listed in FINAL_REPORT.md with their reasons.
