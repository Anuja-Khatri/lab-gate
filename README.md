# lab-gate

A plan-checking safety gate for autonomous labs. It checks a proposed experiment
plan against written invariants before the plan runs and returns exactly one of:

- **PASS** with a proof certificate,
- **BLOCK** with a counterexample step sequence,
- **ABSTAIN** with a reason, routed to a human queue.

No decision path reads any free-text field. lab-gate is built on the public
[`helao-async`](https://github.com/High-Throughput-Experimentation/helao-async)
framework and evaluated inside its OER electrocatalysis simulator (OERSIM). It is the
first outside project built on helao-async (verifiable from that repo's contributor
history); it is not a contribution to, or endorsed by, that project or any company.

## Why

Autonomous labs run agents that execute physical experiments in loops, and
lab-as-a-service platforms share instruments across several partners. Reasoning
agents are good at breaking a goal into composable steps, which is also how a
forbidden goal can be split into innocent-looking steps. A gate that fences written
safety and protocol rules, and routes everything novel to a human, is one way to keep
that structure honest. The gate never judges scientific merit and never blocks
surprising-but-safe science; it is a verifier and an evaluation environment, not a
rival reasoning method.

## Three ways to judge it

1. **Watch** — `make demo` reproduces the headline numbers from cached model
   responses, without API keys (also packaged as a Docker image under `docker/`). A
   recorded cast is in `media/`.
2. **Read** — this README, `docs/FINAL_REPORT.md`, `docs/POST.md`, and the static
   results page in `site/` (every number renders from `results/registry.json` under a
   numbers lock).
3. **Reproduce** — `make ci` (lint, tests, taint test, static no-reference check,
   secret scan, numbers-lock check), `make sim`, `make equivalence`, `make eval`.

## Quickstart

```
# Work from a parent directory ($WS). lab-gate and helao-async must sit side by side:
#   $WS/lab-gate   $WS/helao-async
git clone <this-repo-url> lab-gate
git clone https://github.com/High-Throughput-Experimentation/helao-async.git
git -C helao-async checkout ba910c4   # the pin the gate is evaluated against

cd lab-gate
make setup                      # uv venv (Python 3.12) + deps; PYTHONPATH -> helao-async
make ci                         # lint + tests + taint + secret scan + numbers lock
make sim                        # deterministic OERSIM closed loop (byte-identical)
make demo                       # reproduce headline numbers from cache (no API keys)
```

`make demo` needs no keys and no network: it recomputes the headline numbers from the
committed cache (`eval/cache/`) and checks them against `results/registry.json`.
Verified from a fresh clone (setup, ci, sim, demo all pass offline).

The LLM arms (LLM gate, LLM attacker) need keys in `$WS/.env`
(`LABGATE_ANTHROPIC_API_KEY`, `LABGATE_OPENAI_API_KEY`, `LLM_BUDGET_USD`); every call
is cached, metered, and budget-capped. `make demo` needs no keys.

## Results summary

See `docs/tables/results.md` (rendered from the registry) and the site. In short, on
the held-out evaluation:

- the typed gate lets through no in-specification static or decomposition attack and
  never false-blocks a benign plan, including the surprise subset; its failures are
  confined to out-of-spec harm and attacks beyond its horizon, where it abstains;
- the LLM gate, given a frontier model, the full rules, and the full plan including
  comments, is an unreliable gate in both model families tested, in opposite
  directions: one is too permissive (lets through ~a quarter of the attacks), the
  other over-blocks benign plans and lets through adaptive attacks with nonzero
  run-to-run variance; giving the permissive LLM the same predicted potential the typed
  gate uses sharply cut its attack misses but did not make it a reliable gate;
- the learned classifier is accurate in-distribution and degrades under adaptive
  attack;
- a third-vendor cross-check (Gemini attacker + Gemini gate) is implemented and
  verified live but its arms are "blocked, not measured" on the available free-tier
  quota, reported honestly empty rather than estimated.

Exact rates with n and 95% CIs are in the registry; this prose states direction only.
The reference and SMT checkers agree on every plan in the equivalence suite, every
BLOCK counterexample replays in the simulator, and the taint test shows no text
channel.

## Limitations

A simulator is not a lab; the invariants are benign stand-ins that model the structure
of real controls; there is no human-agreement evidence; the paid LLM arms ran at
reduced sizes under a spend cap. Full list: `LIMITATIONS.md`. Human checkpoints:
`HUMAN_CHECKPOINTS.md`. Agreement protocol (written, unexecuted): `AGREEMENT_PROTOCOL.md`.

## Attribution and AI disclosure

Built on `helao-async` (MIT) at pin `ba910c4`; the OER CP dataset replayed by OERSIM
originates from measurements associated with doi:10.1039/C8MH01641K. Pattern reuse
(taint test, equivalence harness, cached/metered LLM wrapper, results registry,
numbers lock, secret scan) from the owner's public `consilience-verification` repo;
no domain content was copied. See `NOTICE`.

This project was carried out by Claude Code from a specification written with Claude,
with the owner reviewing and confirming the decision rules. Every non-trivial decision
is logged in `DECISIONS.md`.

## References

- Dwyer, Avrunin & Corbett. Patterns in property specifications for finite-state
  verification. ICSE 1999.
- De Giacomo & Vardi. Linear temporal logic and linear dynamic logic on finite
  traces. IJCAI 2013.
- Shah, Kamath, Li & Shah. Bayesian inference of temporal task specifications from
  demonstrations. NeurIPS 2018.
- Guevarra et al. Orchestrating nimble experiments across interconnected labs
  (HELAO). (verify venue/year before citing in a submission.)
- helao-async repository:
  https://github.com/High-Throughput-Experimentation/helao-async

## License

MIT (see `LICENSE`).
