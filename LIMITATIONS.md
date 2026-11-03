# Limitations

Plain language. Lead with what was measured, then what it means, then what it does
not mean.

1. Built on public `helao-async` at the pinned commit `ba910c4`. Any production fork
   may differ. No claim of relevance to any private system. The soft spots addressed
   (untyped `action_params`, free-text comment fields) are properties of the public
   ancestor, described and hardened as a contribution, never as a vulnerability of
   any company.

2. A simulator is not a lab. All results are scoped to the OERSIM simulated
   environment, including the benign accounting extension (`sim_ext/accounting.py`).
   Numbers do not transfer to a physical lab without re-measurement.

3. The invariants are benign and model the STRUCTURE of real controls (instrument
   protection, accumulation limits, forbidden combinations, protocol ordering,
   budgets). They are not real safety policies. I4's forbidden pair, I7's shared
   budget, the capability sets and the element allowlist are explicitly marked
   stand-ins.

4. Deterministic is not correct. The gate enforces the registry exactly, including
   any error in it. A wrong limit yields a confident wrong verdict. Policy
   authorship is a human checkpoint (H1).

5. Bounded proofs hold only to horizon k = 64 actions unless marked unbounded
   (results/invariant_status.json: the accumulate invariants are bounded; the gate
   ABSTAINS on plans longer than k rather than guessing).

6. I1 model-reality divergence is limited by construction: the gate predicts
   potential from measured history when a composition is already characterised, and
   from a linear surrogate otherwise (D-015). The surrogate under-predicts the
   dataset's overload compositions, but those are not addressable and so cannot be
   measured by the oracle. The broader divergence surface is reported via the
   out-of-spec probes, not hidden.

7. Baseline strength is bounded by the available models and good-faith tuning effort
   (logged in DECISIONS.md). The LLM gate used a frontier model (OpenAI gpt-5.1),
   the full written rules, the full plan including comments, and a prompt tuned on
   the dev split before freezing. A stronger prompt or model might do better.

8. LLM-gate vendor and run sizes (R-03, R-08, D-024). The LLM-gate baseline was
   originally pinned to OpenAI gpt-5.1 and ran once at a reduced grid (attack success
   0.11 static / 0.46 adaptive, benign false-block 0.64, variance 0.30). During the
   round-2 full-size re-run the OpenAI account ran out of credits (HTTP 429), so new
   OpenAI calls were impossible. Per R-03 (vendor unavailable) the full-size LLM-gate
   arms and the information-parity arm were run on Anthropic claude-opus-5-5, and the
   adaptive LLM attacker on claude-sonnet-5-5 (a different model). Consequences,
   disclosed on every LLM metric's caveat and in FINAL_REPORT "Deviations": (a) the
   headline LLM-gate numbers now come from Anthropic opus, not the originally-pinned
   OpenAI gpt-5.1 (whose reduced-grid numbers are reported as a consistent prior-vendor
   datapoint); (b) the LLM gate and the LLM attacker are therefore the same vendor
   (mitigated by using different models). The deterministic arms (typed gate,
   classifier, oracle, programmatic adaptive attacker) ran at full scale and need no
   API. Every LLM-arm number is reported with its exact n.

9. The gradient-boosting classifier uses scikit-learn HistGradientBoosting rather
   than xgboost (D-021; xgboost's wheel could not load its OpenMP runtime on the
   build machine). A GPU fine-tuned transformer text classifier was not run (no GPU).

10. No human-agreement evidence. The builder had no reviewers and no approval logs.
    Gate-human agreement is NOT measured here. The procedure to measure it is written
    and unexecuted in AGREEMENT_PROTOCOL.md.

11. The full orchestration group was not launched in this environment (no conda;
    FastAPI/Bokeh/torch/ZeroMQ absent). Per R-05 the gate was evaluated against the
    OERSIM experiment/sequence plan-makers and the real CP dataset driven in-process,
    preserving the real action models. What was bypassed (the server transport and
    the GP acquisition policy) is documented in DECISIONS.md (D-009).

12. AI-assisted build. This project was carried out by Claude Code from a
    specification written with Claude, with the owner reviewing and confirming the
    decision rules. Every non-trivial decision is logged in DECISIONS.md.
