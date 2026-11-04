# Results table (rendered from results/registry.json; do not edit by hand)

| metric | value | 95% CI | n |
|---|---|---|---|
| abstain.classifier.benign | 0.0 | [0.0, 0.000282] | 13627 |
| abstain.gemini.benign | blocked (not measured) |  | 0 |
| abstain.gemini_parity.benign | blocked (not measured) |  | 0 |
| abstain.llm.benign | 0.003401 | [0.000601, 0.019012] | 294 |
| abstain.llm_gpt51.benign | 0.010204 | [0.003476, 0.029566] | 294 |
| abstain.llm_parity.benign | 0.0 | [0.0, 0.012898] | 294 |
| abstain.typed.benign | 0.0 | [0.0, 0.000282] | 13627 |
| abstain_breakdown.typed | out_of_schema_action=0; schema_invalid=5; provenance_invalid=0; beyond_horizon=1; unknown_campaign_class=0; unknown_substrate=0; solver_timeout=0; reference_smt_disagree=0 |  | 6 |
| attack.classifier.adaptive | 0.316667 | [0.261097, 0.378013] | 240 |
| attack.classifier.static_decomp | 0.243243 | [0.133614, 0.401173] | 37 |
| attack.gemini.static_decomp | blocked (not measured) |  | 0 |
| attack.gemini_attacker_vs_gemini | blocked (not measured) |  | 0 |
| attack.gemini_attacker_vs_typed | blocked (not measured) |  | 0 |
| attack.gemini_parity.static_decomp | blocked (not measured) |  | 0 |
| attack.llm.adaptive | 0.277778 | [0.158483, 0.439925] | 36 |
| attack.llm.static_decomp | 0.277778 | [0.158483, 0.439925] | 36 |
| attack.llm_attacker_vs_llm | 0.0 | [0.0, 0.242494] | 12 |
| attack.llm_attacker_vs_typed | 0.0 | [0.0, 0.242494] | 12 |
| attack.llm_gpt51.adaptive | 0.458333 | [0.278913, 0.649251] | 24 |
| attack.llm_gpt51.static_decomp | 0.108108 | [0.042852, 0.247085] | 37 |
| attack.llm_parity.static_decomp | 0.083333 | [0.028749, 0.218267] | 36 |
| attack.typed.adaptive | 0.0 | [0.0, 0.015754] | 240 |
| attack.typed.static_decomp | 0.0 | [0.0, 0.094058] | 37 |
| attack_curve.classifier | [curve, 10 points] |  | 240 |
| attack_curve.llm | [curve, 10 points] |  | 36 |
| attack_curve.typed | [curve, 10 points] |  | 240 |
| decided_coverage.classifier.benign | 1.0 |  | 13627 |
| decided_coverage.llm.benign | 0.997 |  | 294 |
| decided_coverage.llm_parity.benign | 1.0 |  | 293 |
| decided_coverage.typed.benign | 1.0 |  | 13627 |
| dev.llm_gemini.agreement_vs_oracle | 0.633 |  | 30 |
| dev.llm_gpt51.agreement_vs_oracle | 0.5 |  | 30 |
| equivalence.reference_vs_smt | 1.0 |  | 12000 |
| falseblock.classifier.benign | 0.069568 | [0.065416, 0.073962] | 13627 |
| falseblock.classifier.surprise | 0.00202 | [0.000554, 0.007336] | 990 |
| falseblock.gemini.benign | blocked (not measured) |  | 0 |
| falseblock.gemini.surprise | blocked (not measured) |  | 0 |
| falseblock.gemini_parity.benign | blocked (not measured) |  | 0 |
| falseblock.gemini_parity.surprise | blocked (not measured) |  | 0 |
| falseblock.llm.benign | 0.003401 | [0.000601, 0.019012] | 294 |
| falseblock.llm.surprise | 0.0 | [0.0, 0.012769] | 297 |
| falseblock.llm_gpt51.benign | 0.642857 | [0.586567, 0.695463] | 294 |
| falseblock.llm_parity.benign | 0.003401 | [0.000601, 0.019012] | 294 |
| falseblock.llm_parity.surprise | 0.0 | [0.0, 0.012769] | 297 |
| falseblock.typed.benign | 0.0 | [0.0, 0.000282] | 13627 |
| falseblock.typed.surprise | 0.0 | [0.0, 0.003865] | 990 |
| latency.p50_ms | 2.917 |  | 1000 |
| latency.p95_ms | 20.378 |  | 1000 |
| llm.spend_usd | 93.8221 |  | 5131 |
| replay.counterexample_validity | 1.0 |  | 458 |
| spec_coverage.out_of_spec_reached | 0.205882 | [0.103495, 0.367984] | 34 |
| taint.sentinel_channel | 0 |  | 1000 |
| variance.llm.flip_rate | 0.033613 | [0.013148, 0.083249] | 119 |
| variance.llm_gemini.flip_rate | blocked (not measured) |  | 0 |
| variance.llm_gpt51.flip_rate | 0.3 | [0.198982, 0.425087] | 60 |
| variance.typed.flip_rate | 0.0 |  | 120 |
