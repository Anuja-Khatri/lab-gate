# Agreement protocol

**Written and unexecuted. The builder had no access to reviewers or approval logs.**

This is the complete procedure a lab's own reviewers would use to measure how well
the gate agrees with human judgement. It is a protocol, not a result. No number in
this repository comes from it.

## 1. Sampling plan

- Draw a stratified sample from the lab's real approval logs: stratify by requester
  class (internal / external partner), by campaign class, and by the upstream
  human decision (approved / rejected / escalated). Target at least 384 plans for a
  +/-5% margin at 95% confidence on a single proportion; more if subgroup rates are
  wanted.
- Freeze the sample and its stratification before any gate is run on it.

## 2. Independent dual review

- Two qualified reviewers independently label each sampled plan ALLOW / BLOCK /
  ESCALATE, blind to each other and to the gate's verdict.
- Disagreements are recorded, not resolved by one reviewer; adjudication (if any)
  is a third, logged step.

## 3. Inter-reviewer agreement as the baseline

- Compute Cohen's kappa between the two reviewers. This is the ceiling: the gate
  cannot be expected to agree with a human more than two humans agree with each
  other. Report kappa with a bootstrap 95% CI.

## 4. Gate vs reviewer agreement

- Compute Cohen's kappa between the gate's verdict and each reviewer, and against
  the adjudicated label. Report all three with CIs.
- Report the confusion matrix (gate PASS/BLOCK/ABSTAIN x human ALLOW/BLOCK/ESCALATE)
  so over-blocking, under-blocking, and abstain-routing are visible separately.

## 5. Abstain-routing analysis

- For every gate ABSTAIN, record what the humans decided. A good abstain routes a
  genuinely ambiguous plan to a human; a bad abstain routes a plan the humans found
  trivial. Report the human decision distribution conditional on ABSTAIN.

## 6. Prospective preregistered variant

- Before the next N live decisions, preregister the hypotheses, the kappa targets,
  and the stopping rule. Run the gate in shadow (advisory only) alongside the humans
  for those N decisions. Compare prospectively. This avoids the optimism of a
  retrospective sample.

## Future work: specifications from approvals

Human approval decisions are acceptability judgements: exactly the input that
Bayesian specification-inference methods (Shah, Kamath, Li & Shah, NeurIPS 2018)
learn temporal-logic specifications from. An operating lab's approval logs could
seed candidate invariants, which humans then review and sign at checkpoint H1. This
is a proposal. It is not built and not tested here.
