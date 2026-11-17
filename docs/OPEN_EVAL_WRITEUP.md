# Checking a lab plan before it runs: an open evaluation for plan gates

*Draft write-up for arXiv, not submitted. Author: Anuja Khatri (independent). Every
number below is copied from `results/registry.json` (locked by `results/NUMBERS_LOCK.json`)
or, where marked, comes from a run of the Inspect task in this repository. The notes
for submission at the end are not part of the paper.*

## Abstract

Autonomous laboratories let software, including language models, propose experiment
plans that robots then execute. A *plan gate* reads each plan before it runs and
decides: run it, block it, or send it to a human. We release an open evaluation for
plan gates, built from the preregistered evaluation of lab-gate, a rule-based gate for
a simulated electrochemistry lab. It has 37 held-out attack plans (field smuggling,
unit games, comment injection, bound and capability violations, budget decomposition
within one plan and across requesters), a seeded stream of benign plans and a stream
of unusual-but-valid plans. Ground truth comes from an oracle that executes each plan
in the simulator and checks the actual trace against the written rules. The
evaluation is packaged as an Inspect task: it runs against lab-gate itself (no API
key), against any language model given the written rules (one command), or against a
user's own gate. Baselines from the registry: lab-gate let through 0 of 37 attack
plans (95% CI upper bound 0.094) and false-blocked none of 13627 oracle-safe benign
plans; a language-model gate given the same rules let through 0.28 of attacks
(n=36), and 0.08 when also given the quantity the typed gate computes. A replay
model reproduces the published language-model numbers exactly inside Inspect at no
cost. All results are from simulation, with benign stand-in rules.

## 1. The problem

A self-driving lab closes the loop: a planner proposes the next experiment, an
orchestrator turns it into instrument actions, and the robot runs them. When the
planner is a language model, a plan can be wrong in ways nobody intended: a
parameter past an instrument's limit, a unit that silently changes a number, a
budget exceeded only by the sum of steps that are each allowed, or a free-text
comment ("approved by safety") that a downstream reader trusts. Checking plans before
execution is an obvious control. Two very different checkers are on offer: a typed,
rule-based checker that decides from the plan's parameters, or a language model
asked to read the rules and the plan. Both claim to be safety checks; there was no
shared, runnable test to compare them on the same plans with the same ground truth.

This evaluation provides one. It does not claim that any gate is safe for a real
lab. It measures, in one simulated setting, how often a gate passes a plan that
breaks the rules it was given, how often it blocks or abstains on a plan that is
fine, and how it handles numbers it cannot read.

## 2. The evaluation

**Setting.** Plans target OERSIM, the oxygen-evolution electrocatalysis simulator of
the public helao-async framework (pinned commit `ba910c4`), driven in-process. A plan
is a typed list of actions (load a plate, measure a composition, deposit, anneal, and
so on) with a requester, a campaign class and optional free-text fields. The rulebook
is lab-gate's 11 seed rules in four kinds: bounds on one action, states that must
never be reached or orderings that must hold, forbidden element combinations, and
running totals that must stay under a limit (instrument, furnace and per-requester
budgets). The rules model the structure of real controls with benign stand-ins.

**Sets.** (i) *Attacks*: the 34 static and decomposition attack plans of the
preregistered held-out suite and 3 cross-requester attacks, in which several
requesters stay within their own budgets but exceed a shared one together (n=37).
(ii) *Benign*: a seeded stream of 10000 policy-style and 10000 random valid plans;
13627 are oracle-safe. (iii) *Surprise*: 1000 unusual-but-valid plans drawn uniformly
over the valid parameter space; 990 are oracle-safe. The language-model arms used the
first 300 plans of (ii) and (iii) (294 and 297 oracle-safe), which is the default in
the Inspect task. Reported separately: (iv) 10 malformed-number probes added after
registration ("1 200 degC", "1.2.3 degC", NaN, infinity), and (v) out-of-spec
coverage: whether an attack plan's run reaches one of four benign harms that no rule
describes.

**Oracle.** The oracle executes the plan in the simulator, with accounting, and
evaluates the rules over the actual state trace. For the instrument-protection rule
it uses the potential replayed from the measured data, not the gate's model of it,
so the oracle and a gate can disagree. An attack counts as harmful when its run
violates the rule it targets; a benign plan counts as safe when its run violates no
rule. Benign-stream plans whose run does violate a rule are left out of the benign
denominators, as in the published evaluation.

**Metrics.** *Let-through*: attack plans the gate passed whose run violated the
targeted rule, over all decided attack plans. *False-block* and *abstain*:
oracle-safe benign (or surprise) plans the gate blocked or sent to a human. Rates
carry Wilson 95% intervals and their n. A gate call that yields no usable verdict is
excluded from n and counted separately, never scored as a verdict. For gates that see
one plan at a time, a cross-requester attack is blocked if any of its plans is
blocked.

**Gates.** The Inspect task offers three kinds: lab-gate's public `check` function;
a language model given the frozen prompt of the published language-model arm (the
written rules, the campaign capabilities and the full plan JSON including its
untrusted comment fields, with a strict-JSON verdict); and any Python function a user
supplies. A parity variant of the model prompt adds, per measurement, the predicted
potential that lab-gate's instrument rule uses.

## 3. Baseline results

From the registry (preregistered held-out run, one seed per stream).

| arm | let-through, attacks | false-block, benign | abstain, benign | false-block, surprise |
|---|---|---|---|---|
| lab-gate (typed) | 0.00 [0.00, 0.094058] n=37 | 0.00 [0.00, 0.000282] n=13627 | 0.00 [0.00, 0.000282] n=13627 | 0.00 [0.00, 0.003865] n=990 |
| learned classifier | 0.243243 [0.133614, 0.401173] n=37 | 0.069568 [0.065416, 0.073962] n=13627 | 0.00 [0.00, 0.000282] n=13627 | 0.00202 [0.000554, 0.007336] n=990 |
| language-model gate (`llm`) | 0.277778 [0.158483, 0.439925] n=36 | 0.003401 [0.000601, 0.019012] n=294 | 0.003401 [0.000601, 0.019012] n=294 | 0.00 [0.00, 0.012769] n=297 |
| same, parity prompt (`llm_parity`) | 0.083333 [0.028749, 0.218267] n=36 | 0.003401 [0.000601, 0.019012] n=294 | 0.00 [0.00, 0.012898] n=294 | 0.00 [0.00, 0.012769] n=297 |
| earlier language-model gate (`llm_gpt51`) | 0.108108 [0.042852, 0.247085] n=37 | 0.642857 [0.586567, 0.695463] n=294 | 0.010204 [0.003476, 0.029566] n=294 | not measured |

The registry's caveats name the model and vendor of each language-model arm; the
`llm` arms ran on a different vendor's model than the earlier arm, after the earlier
vendor's account ran out of credits. The two language-model gates failed in opposite
directions: one let through more than a quarter of the attacks while deciding almost
every benign plan; the other blocked most benign plans. Giving the model the same
predicted quantity the typed gate uses cut its let-through from 0.28 to 0.08 within
one vendor and model. On the separately reported sets: 20.6% of the static and
decomposition attack plans (n=34) reached a harm no rule describes, and lab-gate
abstained on all 10 malformed-number probes.

**Reproduced inside Inspect** (runs in this repository, logs in
`inspect_eval/logs/`): lab-gate gives exactly the registry's four numbers above when
run on the full streams; the replay model gives exactly the registry's numbers for
both `llm` arms, value, interval and n, with each arm's one undecided attack plan
counted as an error; the classifier, plugged in as a user-supplied gate, gives the
registry's attack number exactly. Also from the run here: lab-gate passed none of the
7 out-of-spec plans, because each also breaks a rule it was given; this says nothing
about a plan that breaks no given rule, which a rule-based gate passes.

The registry also holds results this task does not cover: adaptive attackers (a
programmatic attacker found no let-through against lab-gate in n=240 trajectories,
and 0.32 against the classifier), run-to-run variance, latency, and the agreement of
lab-gate's reference checker with an independent SMT encoding (1.0, n=12000).

## 4. How to run

From a clone of `github.com/Anuja-Khatri/lab-gate` (Python 3.12 or newer):

```
uv sync --extra inspect
uv run lab-gate fetch-data
uv run inspect eval inspect_eval/lab_gate_eval/lab_gate_eval.py@lab_gate_plan_gate --model none
uv run inspect eval inspect_eval/lab_gate_eval/lab_gate_eval.py@lab_gate_plan_gate -T gate=model --model <provider>/<model>
```

The first eval command runs lab-gate as the gate offline in about half a minute; the
second runs any model Inspect supports, with the provider's API key. `-T replay=true`
with `-T gate=model` replays the published responses; `-T gate=custom -T
gate_fn=module:function` plugs in another gate; `-T benign=full` uses the full
streams. `fetch-data` downloads one dataset file from helao-async at a pinned commit
and checks its SHA-256. Details: `inspect_eval/README.md`.

## 5. Limits

- *Simulation only.* One simulated lab of one kind; no number transfers to physical
  equipment without re-measurement.
- *Benign stand-in rules and harms.* The rules model the structure of real controls,
  not real safety policies; the attacks aim at those stand-ins.
- *Specification coverage.* A rule-based gate cannot see harm no rule describes;
  20.6% of the attack plans (n=34) reached such harm. This is reported separately and
  is not in the headline.
- *Small n.* 37 attack plans; 294 and 297 oracle-safe plans in the default samples.
  One attack plan moves the let-through rate by 1/37. The intervals are wide.
- *The oracle is a definition.* "Must not run" means "violates the given rules in
  the simulated trace". It does not cover harms outside the rules.
- *Fixed, non-adaptive plans; one prompt.* The plans do not adapt to the gate. A
  model is scored with one frozen prompt and strict-JSON output; a better prompt or
  model may score differently. The prompt was tuned in good faith on a separate
  development split before the held-out run.
- *No human agreement data.* How often lab-gate's verdicts agree with a human
  reviewer is not measured; the protocol is written but not executed.

## 6. Availability

Code, plans, oracle labels, Inspect task and logs: `github.com/Anuja-Khatri/lab-gate`
(MIT), directory `inspect_eval/`. Report: doi:10.5281/zenodo.23954617.
Preregistration: osf.io/jxhfe. lab-gate is built on the public helao-async framework
(MIT) and uses its OER simulator and the OER dataset it ships (associated with
doi:10.1039/C8MH01641K); it is an independent project, not part of or endorsed by
helao-async. The build and this write-up were carried out with AI assistance; the
author reviewed the decisions and is responsible for the content.

---

## Notes for submission (not part of the paper)

**Format.** arXiv prefers TeX; a PDF is also accepted. Convert this file (for example
with pandoc to LaTeX), check the tables, and keep it within about four pages.

**Category.** Primary `cs.AI`; cross-list `cs.CR` (attacks on a checker) and, if
wanted, `cs.RO`. This is a research article with new measurements, not a review or
position paper (arXiv's computer science section now asks for proof of peer review
for those two types; that rule does not apply here).

**AI use.** arXiv asks authors to report significant use of generative AI tools in
the work and holds every listed author fully responsible for the content; AI tools
may not be listed as authors. The disclosure sentence in section 6 covers this; Anu
must read and stand behind every claim before submitting.

**Endorsement (read 17 Nov 2026 from arXiv's endorsement help page and its
21 Jan 2026 policy update).** A first-time submitter to a category must be endorsed
for it. Since 21 January 2026 there are two routes:

1. *Automatic*: an institutional email address on the arXiv account **and** prior
   authorship of a paper already in the same endorsement domain (claimed in the
   account). An institutional email alone no longer qualifies.
2. *Personal endorsement* by an established arXiv author who is registered as an
   author of enough papers in that endorsement domain, submitted between three
   months and five years ago, and who is endorsed there themselves. arXiv staff do
   not endorse.

For computer science the whole `cs` archive is one endorsement domain. As an
unaffiliated author with no prior arXiv paper, Anu takes route 2:

1. Create or log in to her arXiv account; add her ORCID.
2. Start a new submission and choose `cs.AI` as the primary category. arXiv emails an
   endorsement request with a six-character code and a link.
3. Find one or two people who know her or her work and who have recent `cs` papers.
   On any arXiv abstract page, "Which authors of this paper are endorsers?" shows who
   can endorse. Good candidates are authors of papers this write-up builds on or
   cites (autonomous-lab safety, plan checking, LLM safety evaluation).
4. Write to them individually (not a mass email), with the endorsement link, a link
   to the draft and to the repository, and her ORCID. arXiv advises against emailing
   many endorsers at once or repeatedly.
5. One positive endorsement is enough for the domain. Then finish the submission.
   If there is a problem, arXiv's Endorsement Policy Feedback Form is the contact.

After the paper is announced, use its versioned URL (`/abs/XXXX.XXXXXv1`) in the
Inspect Evals register submission (`docs/INSPECT_EVALS_SUBMISSION.md`).
