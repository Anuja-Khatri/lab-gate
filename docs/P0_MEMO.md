# P0_MEMO: how OERSIM plans flow, where the gate attaches, and what state exists

Read-only study of `helao-async` at pin `ba910c4` (commit dated 2026-10-19) and the
owner reference repo `refs/consilience-verification`. No code in helao-async or refs was
modified. This memo is the basis for Phases 2 to 5.

All paths below are relative to `$WS/helao-async/`.

---

## 1. How a plan flows from the decision step to dispatch

OERSIM is an active-learning loop over catalyst **compositions**. A `plate` holds a fixed
set of addressable compositions (each a vector of integer atomic fractions over the plate's
elements). The loop measures a composition with a simulated chronopotentiometry (CP) run,
refits a Gaussian-process (GP) surrogate, then decides whether to stop or requeue itself.

### The library (what authors write)
- `helao/deploy/test/sequences/OERSIM_seq.py` -> `OERSIM_activelearn(init_random_points,
  stop_condition, thresh_value)` builds ONE planned experiment `OERSIM_sub_activelearn`
  via `ExperimentPlanMaker` (`epm.add(...)`).
- `helao/deploy/test/experiments/OERSIM_exp.py` -> four `@experiment` functions build
  **planned actions** via `ActionPlanMaker` (`apm.add(server, action_name, params, ...)`):
  - `OERSIM_sub_load_plate` -> CPSIM.change_plate, CPSIM.get_loaded_plate, GPSIM.initialize_plate
  - `OERSIM_sub_measure_CP` -> CPSIM.get_loaded_plate, GPSIM.acquire_point, CPSIM.measure_cp, GPSIM.update_model
  - `OERSIM_sub_decision` -> CPSIM.get_loaded_plate, GPSIM.check_condition
  - `OERSIM_sub_activelearn` = measure_CP actions ++ decision actions

### Value passing (`to_global` / `from_global`)
Actions declare `to_global_params` (write named `action_params` keys into
`Orch.global_params`) and `from_global_act_params` (read them back into the next action's
params at dispatch). Example chain: `get_loaded_plate` writes `_loaded_plate_id`;
`acquire_point` reads it as `plate_id` and writes `_feature`; `measure_cp` reads `_feature`
as `comp_vec`. In the standalone MicroOrch runner
(`helao/deploy/test/runners/oersim_runner.py`) this is done explicitly with a `GLOBALS`
dict (`_capture` / `_inject`), which is the exact R-05 in-process pattern.

### The self-requeue (the "decision step")
`OERSIM_sub_decision` adds a `GPSIM.check_condition` action. At run time the GPSIM driver's
`check_condition` (see `servers/action/gpsim_server.py:135`) evaluates the stop rule and, if
unmet, calls the orchestrator's `/insert_experiment` endpoint to enqueue another
`OERSIM_sub_activelearn`. This is where a NEW plan is proposed by the running loop.

### Orchestrator dispatch path (`helao/hexagon/app/`)
1. `orch_host.py:564` `insert_experiment` (POST, private) -> `add_experiment`
   (`orch_host.py:376` / `orch_queues.py:366`): appends an `Experiment` to `experiment_dq`.
   **This is the decision-step entry: a proposed plan enters the queue here.**
2. `orch_host.py:980` `dispatch_loop_task` pulls work: `loop_task_dispatch_sequence` ->
   `loop_task_dispatch_experiment` -> `loop_task_dispatch_action`.
3. `orch_dispatch.py:1081` `dispatch_experiment()`:
   - `_stage_experiment()` (:1128) pops the experiment, applies `from_global_exp_params`.
   - `_expand_experiment_actions()` (called :1112) unpacks it into a list `staged_acts`
     of fully-typed `Action` objects with globals applied.
   - **lines 1123-1124**: `for act in staged_acts: orch.action_dq.append(act)` — the plan
     is now a concrete, typed action list about to run.
4. Per action: `orch_dispatch.py:868` `_stage_action_for_dispatch(A)` (runs `init_act`,
   stages output dir) then `orch_dispatch.py:897` `_dispatch_action_locked(...)` POSTs the
   action to its action server. `LoopIntent.estop`/`estopped` is re-checked inside the lock.

---

## 2. Every OERSIM action type and its parameters (the gate's schema set)

Action-level params are the untyped `action_params: dict` on `Action`
(`helao/core/models/action.py:134`). The dispatched endpoints and their typed signatures:

### CPSIM server (`servers/action/cpsim_server.py`) — simulated potentiostat
| action | parameters (name: type = default) | notes |
|---|---|---|
| `measure_cp` | `comp_vec: list[int] = []`, `acquisition_rate: float = 0.2` | `comp_vec` must be an addressable composition tuple on the loaded plate; drives `CPSimExec`. Produces `mean_eta_vrhe` (overpotential) via `_post_exec`. |
| `cancel_measure_cp` | (none) | stops a running measure_cp |
| `get_loaded_plate` | (none) | returns `_loaded_plate_id`, `_orch_key/_orch_host/_orch_port` |
| `change_plate` | `plate_id: int = 0` | switches loaded plate; returns `_loaded_plate_id` |

### GPSIM server (`servers/action/gpsim_server.py`) — GP surrogate
| action | parameters | notes |
|---|---|---|
| `initialize_global` | `num_random_points: int = 5`, `random_seed: int = 9999` | resets all plate state |
| `initialize_plate` | `plate_id: int = 0`, `num_random_points: int = 5`, `reinitialize: bool = False` | seeds priors |
| `get_progress` | `plate_id: int = 0` | returns progress record |
| `acquire_point` | `plate_id: int = 0` | picks next EI composition -> `_feature` |
| `update_model` | `plate_id: int = 0` | refits surrogate (`GPSimExec`) |
| `check_condition` | `plate_id: int=0`, `stop_condition: str="max_iters"`, `thresh_value: float\|int=10`, `repeat_experiment_name: str`, `repeat_experiment_params: dict`, `repeat_experiment_kwargs: dict`, `orch_key: str`, `orch_host: str`, `orch_port: int=0` | the decision step; may requeue |

`stop_condition` is the enum `StopCondition` = {none, max_iters, max_stdev, max_ei}
(`helao/deploy/test/param_models.py:18`). Authoring params use pydantic models with
`extra="forbid"`, `use_enum_values=True` (`param_models.py:36`) — the exact typed-boundary
pattern Phase 2 extends to the action level.

Phase 2 writes one strict schema per action type above. **10 action types total**
(4 CPSIM + 6 GPSIM); `initialize_global`, `get_progress`, `cancel_measure_cp` are not on
the active-learning path but are real endpoints and get schemas for completeness.

### Physics grounding for invariant I1
CP data is `oer13_cps.pzstd` (1.26 MB, replayed real measurements at fixed 3 mA/cm^2).
`drivers/data/oer_metrics.py:calc_eta` reads the trace's `erhe_v` column and returns
overpotential `eta = mean(last 4 s of erhe_v) - 1.23 V`. Current is fixed (3 mA/cm^2); the
natural I1 "instrument protection" quantity is the measured potential `erhe_v` / overpotential
`eta` per composition, available per addressable `comp_vec` directly from the dataset.

---

## 3. Exact gate attach point (file + function + line)

**Primary (decision-step gate, P5.1):** wrap the point where a proposed plan becomes a
concrete typed action list, i.e. the `staged_acts` list inside
`helao/hexagon/app/orch_dispatch.py :: dispatch_experiment` at **lines 1112-1124** (just
after `_expand_experiment_actions()` returns `staged_acts`, before the
`orch.action_dq.append(act)` loop). The gate checks the full typed plan there: PASS -> append;
BLOCK -> do not append, log; ABSTAIN -> route to `results/abstain_queue.jsonl` and hold.

Equivalently, the plan can be intercepted one step earlier at the queue entry
`orch_host.py :: insert_experiment` (**line 564**), which is exactly the decision-step
requeue the GPSIM `check_condition` calls.

**Secondary (dispatch gate, P5.2):** per-action interception at
`orch_dispatch.py :: _stage_action_for_dispatch` (**line 868**) / `_dispatch_action_locked`
(**line 897**), catching actions that did not originate from the decision step.

We attach by **wrapping / configuration-level injection**, never editing helao-async
(hard rule). In this environment the full orchestrator group is unlikely to launch (no conda,
no torch; see Section 5), so P5 implements the gate against the in-process driving path
(the MicroOrch pattern from `oersim_runner.py`, where `staged_acts` is the planned-action
list), which preserves the same action models and attach semantics. The exact upstream
function+line above is recorded so the owner can place the identical check in a live orch.

---

## 4. Native vs accounting (R-06) state table

The OERSIM world natively tracks only: loaded plate id, per-plate GP priors/progress, the
acquired `_feature` (next comp_vec), and per-measurement `mean_eta_vrhe`. The invariants
(I1-I8) model the STRUCTURE of lab controls with benign quantities that OERSIM does not keep.
Per R-06, `sim_ext/accounting.py` adds a benign accounting wrapper that derives each missing
quantity deterministically from action parameters. **No helao-async edits.**

| quantity (invariant) | native? | source / update rule (R-06) |
|---|---|---|
| loaded plate id | native | `change_plate` param / `get_loaded_plate` |
| composition `comp_vec`, elements, fracs | native (dataset) | from `measure_cp.comp_vec` -> dataset `el_str`, fracs |
| predicted potential `erhe_v` / overpotential `eta` (I1) | native (dataset) | `calc_eta` over the composition's stored CP trace |
| predicted current | native (fixed 3 mA/cm^2) | dataset constant; I1 compliance also bounds `erhe_v` |
| cumulative sputter-target consumption per element (I2) | **accounting** | each `measure_cp` consumes target mass per element proportional to its atomic fraction in `comp_vec` (benign unit "target-units"); summed per element per campaign |
| anneal temperature (I3) | **accounting** | benign param added to the typed boundary for an `anneal`-class action stand-in; bounded by substrate limit |
| furnace occupancy / time (I3, I6) | **accounting** | fixed furnace-minutes per measurement/anneal action; summed |
| forbidden element pairing (I4) | native (dataset) | element set of `comp_vec` from `el_str` |
| screening-QC-passed flag per sample (I5) | **accounting** | set when a screening `measure_cp` on a sample completes; durability step requires it true |
| instrument hours per campaign (I6) | **accounting** | fixed instrument-minutes per measurement; summed |
| acid volume per campaign (I6) | **accounting** | fixed acid-volume per measurement; summed |
| shared instrument-hours across requesters, per window (I7) | **accounting** | sum of per-requester instrument-minutes over a scheduling window |
| requester id + class (I7, allowlist) | **accounting (provenance)** | carried in plan provenance; boundary validates `requester` {id, class in internal_agent|external_partner|any} |
| campaign class + exposed action-type set (I8) | **accounting (provenance)** | declared per campaign class; action outside the set never passes |

Every added quantity, its unit, and its update rule will be documented in
`sim_ext/accounting.py` and in METHODS.md. Numeric limits (P3.2) are set from OERSIM's own
parameter ranges so typical benign plans pass and decomposition attacks have room.

---

## 5. How action_params and comment fields travel (quarantine targets, P2.3)

- `action_params: dict` (`core/models/action.py:134`) is **untyped** — the documented soft
  spot of the public ancestor. The gate's typed boundary (Phase 2) replaces trust in this
  dict with one strict pydantic model per action type (`extra="forbid"`).
- Free-text fields that must be stripped before the checker sees a plan (P2.3), with source:
  - `action_comment: Optional[str]` — `core/models/action.py:57`
  - `experiment_comment: Optional[str]` — `core/models/experiment.py:51`
  - `experiment_label: Optional[str]` — `core/models/experiment.py:114`
  - `sequence_comment: Optional[str]` — `core/models/sequence.py:48`
  - `sequence_label: Optional[str] = "noLabel"` — `core/models/sequence.py:47`
- These travel attached to the Action/Experiment/Sequence models through the whole dispatch
  path. `quarantine.py` strips them before anything downstream; the stripped text is stored
  only in the receipt (`gate/receipts.py`), never passed to `gate/checker/` or `gate/verdict.py`.
  A static no-reference check (P2.4) asserts those modules never name these fields.

---

## 6. Reference patterns to reuse (P0.3) — patterns only, no consciousness-domain content

From `refs/consilience-verification` (owner's public repo). We reuse the mechanism, not the
vocabulary or data:

| lab-gate target | reference | pattern reused |
|---|---|---|
| `tests/test_no_text_channel.py` (P2.4) | `logic/no_text_channel_test.py` | taint every free-text field with a sentinel across generated inputs; assert verdicts byte-identical and sentinel never in checker I/O; plus a static grep-proof the checker never reads the fields. |
| `gate/checker/equivalence.py` (P4.5) | `logic/equiv.py` | run two independent implementations (reference vs SMT) over persisted + seeded synthetic edge cases; compare verdict sets exactly; write a divergences.md; register the rate; exit nonzero if < 1.0. |
| `eval/llm.py` (P6.1) | `pipeline/llm.py` | one wrapper for all model calls: dotenv key load into process only, sha256 request-hash disk cache, provenance, retry+backoff, per-task token+$ meter vs budget with a hard cap, JSON-fence stripping. |
| `results/registry.json` + `eval/metrics.py` (P8.4) | `pipeline/registry.py` | `Registry.upsert(metric_id, value, n, ci_lo, ci_hi, task, runid, tags, caveats)`; `save()` sorts + validates; every doc number renders from here. |
| `results/NUMBERS_LOCK.json` (P8.4) | `pipeline/numbers_lock.py` | verify preconditions present, then lock a registry snapshot (sha256 over the metrics array) and render tables from it; a second snapshot requires regenerating every doc that cited the first. |
| `eval/` secret scan in `make ci` (P1.5) | `pipeline/check_secrets.py` | git-tracked-tree scan for full key-shaped strings (prefix + >=20 tail); allowlist for lines that merely name a pattern; never echo values, only file:line + pattern name. |

Also noted: `harness/` in helao-async (capture/mutate/normalize/parity/freeze) is a
golden-master/mutation toolkit; not required by the gate but confirms the repo's taste for
deterministic, frozen, byte-identity testing, which `make sim` byte-identity (P1 acceptance)
and the gate-disabled byte-identity test (P5.4) match.

---

## 7. R-05 / environment posture (to execute in P1.3)

Full-group launch (`python launch.py demo0`) needs the `helao` conda env (Python 3.14) with
FastAPI + Bokeh + torch/gpytorch and free ports 8001-8003/5001-5003. This machine has no
conda and a heavy GP stack; R-05 fallback is expected: drive the OERSIM experiment/sequence
plan-makers and the simulated CP driver's dataset directly in-process (the `oersim_runner.py`
MicroOrch pattern), preserving the action models, and compute accounting + native eta from
the real dataset. The GP acquisition policy (`acquire_point`, needs torch) will be replaced
for benign-plan GENERATION by direct sampling of real addressable compositions from the
dataset, documented as a bypass; the oracle never needs the GP (it executes a GIVEN plan and
reads the real CP trace). P1.3 records exactly what launched vs what was bypassed. No fake
simulator is written: compositions, CP traces, and eta are the real dataset values.
