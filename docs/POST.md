# A plan-checking gate for autonomous labs, and an honest test of it

Autonomous labs now run agents that execute physical experiments in loops, with no
manual handoff between deciding what to try and trying it. Lab-as-a-service platforms
go further and share instruments across several outside partners. In that setting the
thing worth checking is not whether an agent is clever but whether the next plan it
dispatches obeys the lab's written safety and protocol rules. lab-gate is a small,
open gate that does exactly that, and this post is mostly about how it was tested,
because the test is the point.

## What the gate does

Before a plan runs, the gate checks it against a registry of written invariants and
returns one of three answers: PASS with a proof certificate, BLOCK with a concrete
counterexample, or ABSTAIN with a reason that routes the plan to a human. It is built
on the public helao-async framework and evaluated inside that framework's OER
electrocatalysis simulator, so every quantity is benign: compositions, potentials,
instrument time, consumables, furnace schedules, a forbidden element pairing, a
shared-instrument budget across partners.

Three design choices matter. First, the gate reads only typed fields. Every comment
and label is stripped before the checker sees the plan; a test injects a sentinel
into every free-text field of a thousand plans and shows the verdict never changes
and the sentinel never reaches the checker. An instruction like "approved by safety"
in a comment has no power here, by construction. Second, the gate is checked two ways:
a plain Python evaluator and an independent Z3 encoding, run against twelve thousand
plans; they agree on every one, and every BLOCK is replayed in the simulator and
confirmed. Third, the gate never judges scientific merit. It fences written rules and
sends everything novel to a human.

## The honest comparison

The interesting question is how a typed gate compares to the alternatives a lab would
actually reach for: a frontier language model asked to judge the plan, and a trained
classifier standing in for a learned safeguard. We gave the language-model gate a
strong reasoning model, the full written rules, and the full plan including its
comments, and we tuned its prompt in good faith before freezing it. We attacked all
three gates with the same static and decomposition suites and with an adaptive
attacker, and we scored success against a ground-truth oracle that runs the plan in
the simulator and checks what actually happened.

The headline chart (attack success vs attacker budget for the three gates, with 95%
confidence intervals) is on the results page in `site/`; the full table with n and
CIs is in `docs/tables/results.md`.

The typed gate let through no in-specification attack: 0.00 on the static and
decomposition suites (n=37) and 0.00 under the adaptive attacker at the full grid
(n=240), and it never false-blocked a benign plan (0.00 of 13627 oracle-safe plans, and
0.00 on the surprise subset of 990 unusual-but-valid plans). An LLM adaptive attacker, a
frontier model generating the attacks rather than the programmatic one, also found no
way past the typed gate: 0 of 12 in the preregistered run, and 0 of 48 in black-box mode
and 0 of 48 in gray-box mode in a declared extension (95% CI 0.00 to 0.074 per mode),
labeled "extension, not preregistered." The language-model gate was unreliable in both
of the model families we could run, in opposite directions. The Anthropic model decided
essentially every one of 294 benign plans (false-block and abstain each 0.003, n=294)
but was too permissive on attacks, letting through 0.28 of the static and decomposition
attacks (n=36) and 0.28 under the adaptive attacker (n=36), with run-to-run variance 0.03
(n=119); giving it the exact predicted potential the typed gate uses (an
information-parity arm) cut its attack success to 0.08 (n=36), so much of its gap was an
information deficit it could not otherwise quantify. The OpenAI numbers come from the
earlier reduced grid: that model went the other way and over-blocked 0.64 of 294 benign
plans (n=294), let through 0.46 of the adaptive attacks (n=24), and changed its own
verdict on 0.30 of 60 plans (n=60) when asked the same question five times (five distinct
repeats). The classifier was accurate on benign plans (false-block 0.07 of 13627 plans,
n=13627) but was broken by 0.24 of the static attacks (n=37) and 0.32 of the adaptive
ones (n=240). The reference and SMT checkers agreed on all 12000 equivalence plans, every
BLOCK counterexample replayed in the simulator, and the taint test found no text channel
over 1000 plans.

A third-vendor cross-check (a Gemini adaptive attacker and a Gemini language-model gate,
to restore gate-and-attacker vendor separation) is implemented and verified live, but
the available Gemini account is free-tier with a ~25-request-per-model quota, so those
arms are reported "blocked, not measured" rather than estimated. The two language-model
families we could run (one too permissive, one over-blocking) already make the point;
the Gemini arms are left honestly empty until a higher-quota key is available.

The surprise subset is the proof that the gate does not police novelty: it is a
thousand unusual-but-valid plans far from the policy's usual proposals, and the
gate's false-block rate on them is reported next to everything else. A gate that
blocked strange-but-safe science would be worse than useless to a lab whose whole job
is strange science.

## Three things the test taught

First, a rule gate is only as good as its rules, and it should say so. When a plan
needs a quantity the gate was never given, it abstains rather than guess. We also
measured four benign harms the gate was deliberately not told about; attacks that
reach them show what any rule-based gate cannot catch. That number is reported
separately and never folded into the headline.

Second, in a loop where today's results train tomorrow's model, protocol invariants
are also validity conditions for the training data. A run that violated the protocol
produced a result that should not be trusted as verified. A gate that enforces the
protocol is, quietly, also keeping the training signal clean.

Third, this evaluation is itself an environment, an attacker, and a verifier: the
same genre as the internal scientific reinforcement-learning environments that
autonomous-science companies say they build at scale. The gate is a verifier and an
evaluation harness. It is not a rival to scaled general models, and it is not an
argument against them; the labs this work addresses engineer verifiers themselves,
at industrial scale. It is one more verifier, made small and auditable.

## Limitations

A simulator is not a lab, and these invariants are benign stand-ins for the structure
of real controls, not real safety policies. There is no human-agreement evidence here;
the builder had no reviewers, and the procedure to measure agreement is written and
unexecuted. The language-model arms ran at reduced sizes under a spend cap, each
number reported with its n. The gate enforces its registry exactly, including any
error in it, which is why policy authorship is a human checkpoint.

This project was carried out by Claude Code from a specification written with Claude,
with the owner reviewing and confirming the decisions. Everything here is reproducible
without API keys from cached model responses: watch the demo, read the page, or run it
yourself.
