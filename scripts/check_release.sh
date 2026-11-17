#!/usr/bin/env bash
# Release check for lab-gate (see docs/RELEASE.md). Uploads nothing.
#
# 1. builds the sdist and wheel into dist/ and runs `twine check --strict`;
# 2. installs the wheel into a brand-new virtual environment (nothing else in it);
# 3. runs the README quickstart there: the CLI examples (expected exit codes 0/1/2,
#    --json) and the README Python example, compared line by line with its comments.
#
# Usage: bash scripts/check_release.sh        (needs Python 3.12+ as `python3`,
#                                              or set PYTHON=/path/to/python3.12)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
unset PYTHONPATH || true   # test the built package only, never the source tree
PY="${PYTHON:-python3}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

"$PY" -c 'import sys; assert sys.version_info >= (3, 12), f"need Python 3.12+, found {sys.version.split()[0]}"'

echo "== 1. build and twine check"
"$PY" -m venv "$WORK/build-venv"
"$WORK/build-venv/bin/python" -m pip install -q --upgrade pip build twine
rm -rf "$REPO/dist"
"$WORK/build-venv/bin/python" -m build --outdir "$REPO/dist" "$REPO" >"$WORK/build.log" 2>&1 \
  || { cat "$WORK/build.log"; exit 1; }
ls -l "$REPO/dist"
"$WORK/build-venv/bin/twine" check --strict "$REPO"/dist/*

echo "== 2. install the wheel into a brand-new venv"
"$PY" -m venv "$WORK/test-venv"
"$WORK/test-venv/bin/python" -m pip install -q --disable-pip-version-check "$REPO"/dist/lab_gate-*-py3-none-any.whl
BIN="$WORK/test-venv/bin"
"$BIN/python" -I - <<'PY'
import importlib.util
assert importlib.util.find_spec("helao") is None, "helao-async must not be installed here"
assert importlib.util.find_spec("eval") is None, "the eval harness must not be in the wheel"
PY

echo "== 3. README quickstart in an empty folder"
mkdir "$WORK/run" && cd "$WORK/run"
unset PYTHONPATH HELAO_DATASET || true
"$BIN/lab-gate" version
"$BIN/lab-gate" examples .
expect() {  # expect <exit code> <args...>
  local want="$1"; shift
  set +e; "$BIN/lab-gate" "$@" >"$WORK/out.txt" 2>&1; local got=$?; set -e
  if [ "$got" != "$want" ]; then
    cat "$WORK/out.txt"; echo "FAIL: lab-gate $* exited $got, expected $want"; exit 1
  fi
  echo "ok: lab-gate $* -> exit $got ($(grep -m1 '^verdict:' "$WORK/out.txt" || echo 'no verdict line'))"
}
expect 0 check plan_pass.json --rules rules.yaml
expect 1 check plan_block.json --rules rules.yaml
expect 2 check plan_abstain.json --rules rules.yaml
expect 1 check plan_block.json --rules rules.yaml --json
"$BIN/python" -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['verdict']=='BLOCK', d" "$WORK/out.txt"
expect 64 check missing.json

"$BIN/python" - "$REPO/README.md" <<'PY'
import contextlib, io, re, sys
readme = open(sys.argv[1]).read()
block = re.search(r"```python\n(.*?)```", readme, re.S).group(1)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(compile(block, "README python example", "exec"), {})
got = buf.getvalue().splitlines()
# expected output = the trailing "# ..." comment on each print line, or a following
# comment-only line for a print without one
want, lines = [], block.splitlines()
for i, ln in enumerate(lines):
    if ln.startswith("print("):
        m = re.search(r"#\s*(.*)$", ln)
        want.append(m.group(1) if m else lines[i + 1].lstrip("# ").rstrip())
assert len(got) == len(want), (got, want)
for g, w in zip(got, want):
    ok = g.startswith(w[:-3]) if w.endswith("...") else g == w
    assert ok, f"README Python example printed {g!r}, README says {w!r}"
    print(f"ok: {g}")
PY

echo "== release check passed: dist/ is ready (nothing was uploaded)"
