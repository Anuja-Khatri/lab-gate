# Inspect Evals register: submission draft (not submitted)

Prepared for Anu to submit from her own GitHub account. Nothing here has been sent.
Route and requirements were read from `UKGovernmentBEIS/inspect_evals` at commit
`a9f1b2c154b32fa8b3eda6286bcae01499815779` (17 Nov 2026): `register/README.md`,
`EVAL_REGISTER.md`, `.github/ISSUE_TEMPLATE/register-submission.yml` and the
existing `register/*/eval.yaml` entries. Re-read them before submitting; the
register is marked beta and its rules change.

## How the register works

Since 8 May 2026 Inspect Evals no longer takes eval code into its own repository.
An eval that lives in its author's repository is listed by opening a **Register
Eval Submission** issue. A bot reads the issue, derives the entry (`eval.yaml`)
from the arXiv paper and the task file, and opens a pull request. A maintainer
reviews it. Before merge, the submitter uploads logs of two models running the
full task and confirms on the pull request.

## Eligibility: what must be true before submitting

| requirement (from the issue form and register guide) | status |
|---|---|
| Implemented with Inspect AI, task defined with `@task` | done: `inspect_eval/lab_gate_eval/lab_gate_eval.py` |
| Upstream repository is public on GitHub | done: `Anuja-Khatri/lab-gate` |
| A `pyproject.toml` with a `[project]` table, installable with `uv sync` | done. `inspect-ai` is in the optional extra `inspect`, so the install line is `uv sync --extra inspect` (an existing register entry, VoxParity, does the same and says so in its description) |
| `inspect_ai` declared as a dependency | done, as the `inspect` extra (the core package stays minimal on purpose) |
| External assets hosted in version-controlled storage, pinned | done: the plans are in the repository; the one external file (helao-async's `oer13_cps` dataset) is fetched by `lab-gate fetch-data` from helao-async at a pinned commit with its SHA-256 checked |
| **The submitter is a contributor to the repository (at least one commit)** | Anu has authored commits in lab-gate (e.g. `e6a5992`, the current `main`), under the name "Anuja Khatri". Check that the email on those commits is one of the addresses on her GitHub account, so GitHub counts her as a contributor |
| **An arXiv paper the eval implements** (required field; a versioned URL such as `/abs/XXXX.XXXXXv1`) | **not yet.** The write-up `docs/OPEN_EVAL_WRITEUP.md` must be posted to arXiv first; see that file for the endorsement route |
| **Logs of two models running all samples**, uploaded after the bot opens the pull request | **not yet.** See "The two model runs" below |
| The source URL is pinned to a 40-character commit SHA that exists on the remote | ready once Anu chooses the commit (see the Source URL below) |
| One eval per issue | this submission registers one task, `lab_gate_plan_gate`; the two side tasks in the same file are documented, not registered |

## The issue to open

Open: <https://github.com/UKGovernmentBEIS/inspect_evals/issues/new?template=register-submission.yml>

**Title:** `[Register Submission] lab-gate plan-gate evaluation`

**arXiv URL:** the versioned abs URL of the posted write-up, e.g.
`https://arxiv.org/abs/XXXX.XXXXXv1`

**Source URL** (pinned; the anchor is the `@task` line of `lab_gate_plan_gate`,
needed because the file holds three tasks):

```
https://github.com/Anuja-Khatri/lab-gate/blob/<COMMIT_SHA>/inspect_eval/lab_gate_eval/lab_gate_eval.py#L486
```

Use the full 40-character SHA of the commit to be registered. The current
candidate is the tip of branch `wp7-open-eval` (`git rev-parse origin/wp7-open-eval`).
If the branch is merged to `main` first, use the merge commit instead. If the task
file changes, re-check the line number of `@task` above `def lab_gate_plan_gate`.
Do not delete the branch while the register points at one of its commits.

**Maintainers:** leave empty (the submitter is added automatically).

**Optional note for the maintainers** (add at the end of the issue body if the form
allows free text; otherwise post it as the first comment):

> Install with `uv sync --extra inspect`, then run `uv run lab-gate fetch-data` once
> (it downloads a dataset file from helao-async at a pinned commit and checks its
> SHA-256). The task runs with `--model none` against the deterministic gate under
> test, or with any model via `-T gate=model`. Logs are in `inspect_eval/logs/`.

## The entry the bot should produce

For reference, if a maintainer asks for the fields or the bot needs correcting.
Format as in `register/*/eval.yaml` at the commit read above.

```yaml
full_title: "lab-gate: Plan Gates for Autonomous Labs"
common_title: "lab-gate plan gate"
paper_title: "<title of the arXiv write-up>"
description: >-
  Tests a plan gate: a model (or any checker) that reads an autonomous lab's
  experiment plan before it runs and answers PASS, BLOCK or ABSTAIN against written
  rules. Plans come from lab-gate's preregistered evaluation in a simulated
  electrochemistry lab (the OER simulator of helao-async): 37 held-out attack plans
  (field smuggling, unit games, comment injection, bound and capability violations,
  budget decomposition, cross-requester budgets) and the first 300 plans of a seeded
  benign stream and of a surprise stream. Ground truth comes from an oracle that runs
  each plan in the simulator and checks the actual trace. The model sees the written
  rules and the full plan JSON, including untrusted comment fields, and answers in
  strict JSON. Metrics: attack let-through rate, benign false-block and abstain
  rates, surprise false-block rate, each with Wilson 95% CIs; unparseable answers are
  counted as errors, not verdicts. Simulation only, with benign stand-in rules.
  Install with `uv sync --extra inspect`, then run `uv run lab-gate fetch-data` once.
contributors:
- Anuja-Khatri
tasks:
- name: lab_gate_plan_gate
  dataset_samples: 637
  task_path: inspect_eval/lab_gate_eval/lab_gate_eval.py
arxiv: https://arxiv.org/abs/XXXX.XXXXXv1
tags:
- Safety
- Agent
- Science
metadata:
  requires:
    internet: true
source:
  repository_url: https://github.com/Anuja-Khatri/lab-gate
  repository_commit: <COMMIT_SHA>
  maintainers:
  - Anuja-Khatri
```

`internet: true` because `lab-gate fetch-data` downloads one file the first time;
model runs also need the provider's API.

## The two model runs (needed after the pull request opens)

The register asks for logs of **two different models** each running **all samples**
of the task. Small, inexpensive models are acceptable (register guide, FAQ).

What is already in the repository, made without any API call or spend:

- `inspect_eval/logs/`: lab-gate as the gate (`--model none`), and a **replay** of the
  published LLM-gate arm and its parity variant from the committed response cache
  (`-T gate=model -T replay=true`). The replay logs show the task running end to end
  and reproduce the registry exactly, but they are replays of cached responses, not
  fresh model runs, and they are labelled so. Whether the maintainers accept a replay
  as one of the two runs is their decision; plan on two fresh runs.

What Anu does (costs money; the session did not do it):

1. Pick two small models from two providers she has keys for.
2. For each, from a clone at the registered commit:

   ```
   uv sync --extra inspect
   uv run lab-gate fetch-data
   uv run inspect eval inspect_eval/lab_gate_eval/lab_gate_eval.py@lab_gate_plan_gate \
       -T gate=model --model <provider>/<model>
   ```

   Each run is 637 samples, 646 model calls and about one million input tokens; look
   up the provider's current price before running. Reasoning models may need
   `--max-tokens 4096` or more (output that is cut off counts as an error).
3. Check each log in `inspect view`: status success, `.n_errors` small.
4. Remove anything personal from the logs before upload (the register warns that
   logs may be published; the logs record file paths and the git revision).
5. Upload both `.eval` files to the Inspect Evals log store. The register guide says
   to upload "to our log store"; the contribution guide links the uploader at
   <https://logfile-upload.generality.workers.dev/>. Then comment on the pull request
   that the two logs are uploaded, naming the models.

## What happens after

- The bot comments on the issue and opens the pull request; automated checks run
  (public repo, pinned commit, no duplicate name). An automated code review checks
  that the `@task` exists, the task builds a dataset and a scorer, the description
  matches the code, and there are no security problems. It can block with
  `[REGISTER_BLOCK]`; a fix and re-run, or `/appeal`, are the routes.
- A maintainer reviews and merges. The eval then appears in the Inspect Evals
  documentation with generated install and run commands.
- To update later (a new commit), Anu opens an issue with the register entry and the
  new commit, unless she is on the pre-approved contributor list.

## Checklist for Anu

1. Post the write-up to arXiv (`docs/OPEN_EVAL_WRITEUP.md`; endorsement first).
2. Confirm her commit email is on her GitHub account.
3. Decide the commit to register (branch tip, or after a merge to `main`).
4. Open the issue above with the arXiv URL and the pinned source URL.
5. When the pull request opens: run two small models, upload both logs, comment.
