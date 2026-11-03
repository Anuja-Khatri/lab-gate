# lab-gate Makefile. Deterministic by construction; see BUILD-SPEC Section 1.
# $WS is the parent of this repo; helao-async (pinned ba910c4) lives there.

REPO := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
WS := $(abspath $(REPO)/..)
HELAO := $(WS)/helao-async
VENV := $(REPO)/.venv
PY := $(VENV)/bin/python
export PYTHONPATH := $(HELAO):$(REPO)
export HELAO_DATASET ?= $(HELAO)/helao/deploy/test/demos/data/oer13_cps.pzstd

SEED ?= 20261103

.PHONY: setup test ci sim eval demo site media clean lint secrets equivalence prereg heldout

setup:
	uv venv --python 3.12 $(VENV)
	uv pip install --python $(PY) -r requirements.txt
	@echo "setup done. PYTHONPATH=$(PYTHONPATH)"

lint:
	$(PY) -m ruff check gate sim_ext eval tests

secrets:
	$(PY) eval/check_secrets.py

test:
	LABGATE_DISABLE_LLM=1 $(PY) -m pytest tests -q

# ci = lint + tests + secret scan (+ numbers-lock once results exist, P8)
ci: lint test secrets
	@if [ -f results/NUMBERS_LOCK.json ]; then $(PY) eval/numbers_lock.py --check || exit 1; fi
	@echo "ci: green"

# sim: full OERSIM closed loop, seeded & deterministic (P1 acceptance).
sim:
	$(PY) -m sim_ext.oersim results/sim_trace.json 2750 8 $(SEED)
	$(PY) -m sim_ext.oersim results/sim_trace_rerun.json 2750 8 $(SEED)
	@cmp -s results/sim_trace.json results/sim_trace_rerun.json \
		&& echo "sim: byte-identical across runs (seed=$(SEED)) OK" \
		|| (echo "sim: TRACES DIFFER" && exit 1)

# equivalence: reference vs SMT checker over the full suite (P4.5). Stub until P4.
equivalence:
	@test -f gate/checker/equivalence.py \
		&& $(PY) -m gate.checker.equivalence \
		|| echo "equivalence: not built yet (Phase 4)"

# eval: baselines + red team + metrics (Phases 6-8). Needs $WS/.env keys for LLM arms.
eval:
	@test -f eval/runner.py \
		&& $(PY) -m eval.runner \
		|| echo "eval: not built yet (Phases 6-8)"

# demo: the reproducible headline-number demo from cache (P9). Stub until P9.
demo:
	@test -f eval/demo.py \
		&& $(PY) -m eval.demo \
		|| echo "demo: not built yet (Phase 9)"

site:
	@test -f site/build.py \
		&& $(PY) site/build.py \
		|| echo "site: not built yet (Phase 9)"

media:
	@echo "media: see docs/OWNER_TODO.md (Phase 9)"

clean:
	rm -f results/sim_trace.json results/sim_trace_rerun.json
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name '.pytest_cache' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "clean done"
