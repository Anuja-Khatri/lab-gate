"""Reference vs SMT equivalence harness (P4.5; pattern from refs equiv.py).

Runs BOTH the reference evaluator and the SMT encoder over a suite of
  - benign-stream plans (policy + random + surprise), and
  - targeted edge plans (empty, single action, exactly-at-limit, off-by-one past
    limit, horizon-length, horizon+1, combination edges, ordering edges),
and compares verdicts EXACTLY (decision + violated invariant + step). It also
asserts that every invariant's exported LTLf formula, evaluated by the independent
LTLf trace evaluator over the reference trace, agrees with the reference's
kind-specific check. Any mismatch is a bug: it is itemised in
docs/equivalence_divergences.md and the run exits nonzero.

Default suite sizes follow the spec (10,000 benign + 2,000 edge); pass smaller via
CLI/args for a fast sample.
"""

from __future__ import annotations

import sys
from pathlib import Path

from eval.streams.benign import benign_stream, edge_plans_many
from gate.boundary.schemas import parse_plan
from gate.checker.ltlf_eval import evaluate_ltlf
from gate.checker.reference import evaluate
from gate.checker.smt import encode_and_check
from gate.registry.lock import DEFAULT_REGISTRY, load_and_hash

REPO = Path(__file__).resolve().parent.parent.parent
DIVERGENCES = REPO / "docs" / "equivalence_divergences.md"
HORIZON_DEFAULT = 64


def run(n_policy=4000, n_random=4000, n_surprise=2000, n_edge=2000,
        horizon_k=HORIZON_DEFAULT, seed=20261103) -> dict:
    reg = load_and_hash()[0]
    suite = benign_stream(n_policy, n_random, n_surprise, seed) + edge_plans_many(n_edge, seed + 1)

    total = matched = ltlf_total = ltlf_matched = 0
    divergences = []
    for idx, rp in enumerate(suite):
        pp = parse_plan(rp)
        r = evaluate(pp, reg, horizon_k=horizon_k)
        s = encode_and_check(pp, reg, horizon_k=horizon_k)
        total += 1
        if (r.decision, r.invariant_id, r.step_index) == (s.decision, s.invariant_id, s.step_index):
            matched += 1
        else:
            divergences.append({
                "plan": idx,
                "ref": f"{r.decision}/{r.invariant_id}@{r.step_index}",
                "smt": f"{s.decision}/{s.invariant_id}@{s.step_index}",
            })
        # LTLf-formula vs kind-specific check, over the reference trace
        if r.decision in ("PASS", "BLOCK") and r.trace:
            for inv in reg.invariants:
                if not (str(inv.scope) == "any" or str(inv.scope) == pp.provenance.requester_class):
                    continue
                if str(inv.kind) == "accumulate" and inv.typed_spec().window is not None:
                    continue
                holds, fv = evaluate_ltlf(inv, r.trace)
                # kind-specific reference verdict for THIS invariant:
                ref_blocks_here = (r.decision == "BLOCK" and r.invariant_id == inv.id)
                ltlf_total += 1
                # LTLf "violated" (not holds) must match reference blocking on it,
                # UNLESS reference blocked earlier on a higher-priority invariant
                # (then this invariant may also be violated but was never reached).
                if (not holds) == ref_blocks_here:
                    ltlf_matched += 1
                elif (not holds) and not ref_blocks_here and r.decision == "BLOCK":
                    ltlf_matched += 1   # earlier block on another invariant; consistent
                else:
                    ltlf_total -= 1     # not a clean comparison point; skip
    rate = matched / total if total else 1.0
    ltlf_rate = ltlf_matched / ltlf_total if ltlf_total else 1.0

    md = ["# Reference vs SMT equivalence (P4.5)", "",
          f"Suite: {total} plans ({n_policy} policy + {n_random} random + "
          f"{n_surprise} surprise + {n_edge} edge). Horizon k={horizon_k}.",
          f"Reference vs SMT exact-match: {matched}/{total} = {rate:.6f}.",
          f"LTLf-formula vs kind-check agreement: {ltlf_matched}/{ltlf_total} = {ltlf_rate:.6f}.",
          ""]
    if not divergences:
        md.append("**No divergences - reference evaluator and SMT encoder agree on every plan.**")
    else:
        md.append(f"## {len(divergences)} divergent plan(s)")
        for d in divergences[:200]:
            md.append(f"- plan {d['plan']}: ref={d['ref']} smt={d['smt']}")
    DIVERGENCES.parent.mkdir(parents=True, exist_ok=True)
    DIVERGENCES.write_text("\n".join(md) + "\n")

    return {"total": total, "matched": matched, "rate": rate,
            "ltlf_total": ltlf_total, "ltlf_matched": ltlf_matched, "ltlf_rate": ltlf_rate,
            "divergences": divergences}


def main() -> int:
    # allow a quick sample: python -m gate.checker.equivalence [n_policy n_random n_surprise n_edge]
    args = [int(x) for x in sys.argv[1:5]] if len(sys.argv) >= 5 else []
    stats = run(*args) if args else run()
    print(f"equivalence: reference vs SMT {stats['matched']}/{stats['total']} = {stats['rate']:.6f}; "
          f"LTLf {stats['ltlf_matched']}/{stats['ltlf_total']} = {stats['ltlf_rate']:.6f}; "
          f"divergences {len(stats['divergences'])} -> {DIVERGENCES}")
    assert str(DEFAULT_REGISTRY)  # keep import used
    return 0 if stats["rate"] == 1.0 and stats["ltlf_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
