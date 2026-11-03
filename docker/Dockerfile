# Release image (P9.9): reproduce the headline numbers from cached LLM responses,
# without API keys. Build needs network (clone helao-async at the pin + pip);
# `make demo` at runtime is fully offline (cache hits need no key).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git make ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
# helao-async at the inspected pin (read-only; provides the real action models + OER
# dataset that lab-gate drives in-process). Not redistributed inside lab-gate.
RUN git clone https://github.com/High-Throughput-Experimentation/helao-async.git \
    && git -C helao-async checkout ba910c4 || echo "pin unreachable; using default branch (R-01)"

# lab-gate itself (the clean clone; in CI this is the repo root copied in).
COPY . /work/lab-gate

RUN pip install --no-cache-dir -r /work/lab-gate/requirements.txt \
    && pip install --no-cache-dir anthropic openai

ENV PYTHONPATH=/work/helao-async:/work/lab-gate
ENV HELAO_DATASET=/work/helao-async/helao/deploy/test/demos/data/oer13_cps.pzstd
ENV LABGATE_DISABLE_LLM=0
WORKDIR /work/lab-gate
ENTRYPOINT ["bash", "docker/entrypoint.sh"]
