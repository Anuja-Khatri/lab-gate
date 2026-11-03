#!/usr/bin/env bash
# Release-image entrypoint (P9.9): reproduce the headline numbers from cache,
# offline, without API keys. The committed eval/cache/ holds the LLM responses.
set -euo pipefail
echo "lab-gate release image: reproducing headline numbers from cache (no API keys)."
python -m eval.demo
