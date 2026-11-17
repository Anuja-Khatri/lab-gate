# Reference logs

Inspect logs of the runs behind the Results table in `../README.md`. All were made
from a fresh clone of this repository at commit `00ca572` (clean working tree),
installed with `uv sync --extra inspect` and `uv run lab-gate fetch-data`, with
inspect-ai 0.3.290. No model API was called and nothing was spent.
`tests/test_inspect_eval.py` checks that the numbers in these logs equal
`results/registry.json`.

| file | command (after `uv run inspect eval inspect_eval/lab_gate_eval/lab_gate_eval.py`) | what it is |
|---|---|---|
| `typed_default.eval` | `@lab_gate_plan_gate --model none` | lab-gate as the gate, default sets (637 samples) |
| `typed_full_streams_no_samples.eval` | `@lab_gate_plan_gate -T benign=full --no-log-samples --model none` | lab-gate on the full benign and surprise streams (21037 samples). Per-sample records are left out to keep the file small; the scores are in the header, and the run is deterministic |
| `replay_llm.eval` | `@lab_gate_plan_gate -T gate=model -T replay=true --model none` | **replay of cached responses** of the published LLM-gate arm, not a fresh model run |
| `replay_llm_parity.eval` | `@lab_gate_plan_gate -T gate=model_parity -T replay=true --model none` | **replay of cached responses** of the published information-parity arm |
| `typed_malformed.eval` | `@lab_gate_malformed --model none` | lab-gate on the 10 malformed-number probes (reported separately) |
| `typed_out_of_spec.eval` | `@lab_gate_out_of_spec --model none` | out-of-spec coverage of the 34 plans (reported separately) |

Open one with `inspect view --log-dir inspect_eval/logs`.
