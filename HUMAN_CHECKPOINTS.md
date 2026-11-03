# Human checkpoints

This gate is designed to work with human reviewers, not instead of them. The builder
could not staff these checkpoints. They are design slots for the operating lab's own
reviewers.

- **H1 Policy authorship and sign-off.** Humans write and approve the invariants.
  The registry is hashed (`gate/registry/lock.py`); any change requires human
  sign-off and produces a new hash recorded on every downstream verdict.

- **H2 Abstain queue.** Every ABSTAIN goes to a human. Anything outside the
  rule-expressible subset (out-of-schema or novel action, beyond horizon, unmodeled
  state, solver timeout) is always a human decision. The file-backed queue is
  `results/abstain_queue.jsonl`.

- **H3 Upstream candidate approval.** The lab's existing early-stage human approval
  stays upstream and untouched. The gate sits after it, at dispatch; it does not
  remove or replace that approval.

- **H4 Overrides with justification.** A human may override a BLOCK with a recorded
  reason. Overrides are logged and feed policy review (they are evidence that a
  limit may be wrong, see H1).

- **H5 Sampled audit of PASS verdicts.** A human periodically reviews a sample of
  PASS verdicts from the receipts (`results/receipts.jsonl`). This is how gate-human
  agreement is measured over time (see AGREEMENT_PROTOCOL.md).

- **H6 Release review.** Promoting a new gate version or a new registry version
  requires human review of its evaluation results before it goes live.

## Plan flow with checkpoints

```
  requester plan
        |
   [H3] upstream early-stage human approval (unchanged, upstream)
        |
        v
  +----------------------+
  |  lab-gate (at dispatch)
  |  typed boundary -> quarantine free text -> checker (reference + SMT)
  +----------------------+
     |          |            |
   PASS       BLOCK       ABSTAIN
     |          |            |
     |      [H4] human     [H2] human queue
     |      may override    (always a human
     |      with reason      decision)
     v          |            |
  execute       v            v
     |      log + review  decide + (optionally
     |      (feeds H1)     sign a new invariant,
     v                     feeds H1)
  [H5] sampled human audit of PASS verdicts  ---> agreement over time
                                                   (AGREEMENT_PROTOCOL.md)

  [H1] humans author + sign the registry (hashed)   applies to the checker box
  [H6] humans review evaluation results before any gate/registry release
```

## The red button stays

Lab operators today stop bad runs by hand (a red button). The gate does not replace
that button. It adds receipts, routes unclear plans to it (H2), and records overrides
(H4), so the button keeps working as supervision thins and labs go lights-out.
