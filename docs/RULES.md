# Writing rules for lab-gate

This is the specification of the rule file (`rules.yaml`) and of the plan file
(`plan.json`) that `lab-gate check` reads. The bundled seed rules
(`examples/rules.yaml`, identical to `gate/registry/invariants.yaml`) are a complete,
commented example. Run `lab-gate examples` to get a copy.

**Important.** The seed rules are benign stand-ins that model the *structure* of
real lab controls inside the OER simulator. They are not a safety policy. If you
write rules for real equipment, you are responsible for them: the gate enforces
exactly what you write, including any mistake (see `LIMITATIONS.md`).

## 1. What a rule can talk about

lab-gate is not a general rule engine. Rules are written over a fixed vocabulary:
the action types the gate can type-check, the per-step variables the checker
computes, and the quantities it accumulates. `load_rules` refuses a rule that names
anything outside this vocabulary, because the checker would otherwise skip it
silently.

### Action types (the only actions a plan may contain)

| action | parameters (units are converted; bare numbers are in the unit shown) |
|---|---|
| `change_plate` | `plate_id` (int) |
| `get_loaded_plate` | none |
| `initialize_plate` | `plate_id`, `num_random_points` (1..1000), `reinitialize` (bool) |
| `initialize_global` | `num_random_points`, `random_seed` |
| `get_progress` | `plate_id` |
| `acquire_point` | `plate_id` |
| `measure_cp` | `comp_vec`, `acquisition_rate` (0..10) |
| `update_model` | `plate_id` |
| `check_condition` | `plate_id`, `stop_condition` (none, max_iters, max_stdev, max_ei), `thresh_value`, and orchestration fields |
| `cancel_measure_cp` | none |
| `deposit_composition` | `comp_vec`, `thickness` (nm, > 0) |
| `anneal` | `temperature` (degC), `duration` (min, > 0), `substrate` (string) |
| `durability_test` | `comp_vec`, `duration` (min, > 0) |

The first ten are helao-async OERSIM endpoints. The last three are lab-gate
stand-ins for synthesis and long-term testing.

A `comp_vec` is 13 integers, each 0..100, summing to 100: atomic-fraction
percentages over the elements `Ca Ce Co Cu Fe La Mg Mn Ni Sb Sn Ta Zn`, in that
order. Quantities may be bare numbers, strings such as `"350 degC"` or `"1 hour"`,
or `{"value": 350, "unit": "degC"}`. A wrong dimension, NaN, infinity or a
malformed number is refused (the plan ABSTAINs).

### Per-step variables (for `bound` and `reach` rules)

| variable | type | meaning |
|---|---|---|
| `predicted_erhe_v` | number | predicted steady-state potential (V vs RHE) of a step with a `comp_vec`: the measured value if that composition was already characterised on the loaded plate, else a linear surrogate (needs the OER dataset) |
| `anneal_temp_over_limit` | bool | an `anneal` is hotter than its substrate's limit |
| `sample_qc_passed` | bool | this sample (plate + composition) had a screening `measure_cp` earlier in the plan |
| `action_outside_campaign_capability` | bool | the action is not in its campaign class's allowed list |
| `partner_element_not_allowed` | bool | an `external_partner` step uses an element outside `partner_element_allowlist` |
| `action` | string | the action type of the step |

### Accumulated quantities (for `accumulate` rules)

All start at zero and only grow along the plan.

| quantity | grows by |
|---|---|
| `instrument_minutes` | 10 per `measure_cp`, 60 per `durability_test` |
| `acid_volume_ml` | 5 per `measure_cp` or `durability_test` |
| `furnace_minutes` | each `anneal`'s duration |
| `n_measurements` | 1 per `measure_cp` or `durability_test` |
| `sputter_target_consumed` | per element; 1 unit per measurement and `thickness` units per deposit, split by atomic fraction. Use with `per: element`. |

## 2. The rule file

```yaml
version: "my-lab-rules-v1"       # any string; part of the rule-set hash
composition_sum: 100

campaign_classes:                # which actions each campaign class may use
  screening_only: [change_plate, measure_cp, get_progress]

partner_element_allowlist: [Fe, Ni, Co]   # elements external partners may use

invariants:                      # the rules
  - id: R1
    kind: accumulate
    plain_english: Total instrument time must not exceed 120 minutes per campaign.
    scope: any                   # any | internal_agent | external_partner
    rationale: Why this rule exists.
    source: Where the limit comes from.
    spec:
      quantity: instrument_minutes
      agg: sum
      limit: 120
```

Every rule needs `id`, `kind`, `plain_english`, `rationale`, `source` and `spec`.
The `plain_english` text is what a BLOCK reports; it is never read by the checker.
Unknown keys are refused.

### The four kinds

**`bound`**: a limit on one action type.
```yaml
spec:
  action: measure_cp
  predicate: {var: predicted_erhe_v, op: "<=", value: 2.5}   # must hold
```

**`reach`**: a state that must never be reached, or an ordering requirement.
```yaml
spec:
  banned: {var: anneal_temp_over_limit, op: "==", value: true}
```
```yaml
spec:                                    # B may not run unless the predicate holds
  precedence_action: durability_test
  precedence_requires: {var: sample_qc_passed, op: "==", value: true}
```

**`forbid_combo`**: elements that may not appear together in one composition.
```yaml
spec:
  subject: elements
  scope_unit: action
  forbidden_pairs: [[Ce, Mn]]
```

**`accumulate`**: a running total that must stay within a limit.
```yaml
spec:
  quantity: sputter_target_consumed
  agg: sum
  per: element          # optional: element | requester
  limit: 5.0
  window: 200           # optional: shared-lab window, see below
```

Operators: `<=`, `>=`, `<`, `>`, `==`, `!=`.

### Things to know (current behaviour, not configurable)

- **Anneal limits.** Substrate temperature limits are read from the
  `extra.substrate_limits_degC` table of the rule with `id: I3`. If there is no such
  rule, or the substrate is not in it, every `anneal` ABSTAINs (`unknown_substrate`).
- **Campaign classes.** A plan whose `campaign_class` is not listed ABSTAINs
  (`unknown_campaign_class`).
- **Order of checks.** Rules with id `I8` and `ALLOW` are checked first at each
  step; the first violated rule is the one reported.
- **Shared-window rules** (`accumulate` with `window`) are checked only across
  several requesters' plans together (`gate.verdict.decide_merged`), not by
  `lab-gate check` on a single plan. The PASS output says so.
- **Horizon.** The proof covers plans up to 64 actions (`--horizon` to change).
  Longer plans ABSTAIN (`beyond_horizon`).
- **Hash.** The rule-set hash is a SHA-256 over a canonical form of the loaded
  rules, so it changes when a rule changes and not when formatting or comments do.

## 3. The plan file

```json
{
  "requester": {"id": "agent-1", "cls": "internal_agent"},
  "campaign_name": "anneal-series",
  "campaign_class": "synthesis",
  "sequence_comment": "free text; set aside, never read by the gate",
  "actions": [
    {"server": "LABGATE", "action_name": "anneal",
     "action_params": {"temperature": "350 degC", "duration": "30 min", "substrate": "quartz"}}
  ]
}
```

- `requester.cls` is `internal_agent`, `external_partner` or `any`. Missing
  provenance defaults to an internal agent in campaign class `activelearn`.
- `action_comment`, `experiment_comment`, `experiment_label`, `sequence_comment`
  and `sequence_label` are free text. They are removed before checking and never
  affect the verdict.
- An action type not in the table above, or a parameter that fails validation,
  makes the plan ABSTAIN (`out_of_schema_action` / `schema_invalid`).
