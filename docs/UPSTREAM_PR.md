# Upstream contribution draft (for the owner to decide)

This is a DRAFT only. Nothing in lab-gate depends on it being merged. It is not
pushed anywhere. The owner decides whether to open it.

## What it is

A branch `typed-action-params` in a separate local clone at `$WS/helao-async-pr`
(the pinned `ba910c4` checkout; the read-only `$WS/helao-async` is untouched). It
adds the smallest change that lets a downstream project register per-action
parameter schemas over HELAO's otherwise-untyped `action_params` dict.

Two files (the repo's median commit touches ~3 files):

1. `helao/helpers/action_param_schemas.py` (new): a process-global registry,
   `register_action_schema(name, validator)` / `validate_action_params(name, params)`
   / `clear_action_schemas()`. Starts empty.
2. `helao/helpers/premodels.py` (one line + import): `ActionPlanMaker.add` calls
   `validate_action_params(action_name, action_params)` just before building the
   `Action`. With no schema registered it is a no-op, so stock behaviour is
   unchanged (verified: the OERSIM plan-makers build identical plans; registering a
   validator makes it fire).

## Why it is shaped this way

- **Opt-in and no-op by default.** It changes nothing for existing users until a
  downstream explicitly registers a schema. That keeps the risk of regression near
  zero and respects the framework's design (untyped params are intentional
  flexibility).
- **One well-defined place.** Today a downstream wanting typed action parameters
  must fork or wrap. This gives a single, documented seam.
- **Small and in the repo's style.** Two files, a short docstring, no new
  dependency, formatted with `black` (line length 88) per the repo's convention.

## Recommended process (before any PR)

The repository's five-year history contains **no outside contributor**, so there is
no merge precedent for an external contribution. Recommendation:

1. Open a short **issue** first, describing the use case (a downstream safety gate
   that validates typed action parameters) and asking whether a per-action schema
   seam would be welcome. Do not open a PR cold.
2. Only if the maintainers are receptive, open the PR from this branch, describing
   it exactly as what it is: an opt-in, no-op-by-default seam in `helao-async`. Make
   no claim that any company uses or endorses it.
3. Run the repo's own checks first: `black` on the two files, then
   `python run_unit_tests.py` and the relevant `python run_tests.py --filter premodels`.

## How to review the draft locally

```
cd $WS/helao-async-pr
git log --oneline -1          # the single commit on typed-action-params
git show                      # the full diff (2 files)
```

Nothing here is pushed. Publishing, issue-opening, and PR creation are the owner's
decisions (R-12; see OWNER_TODO.md).
