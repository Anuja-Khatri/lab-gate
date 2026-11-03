"""Numbers lock + check (P8.4; pattern from refs pipeline/numbers_lock.py).

`lock`  : render the results table from results/registry.json, compute a sha256 over
          the metrics array, and write results/NUMBERS_LOCK.json (+ stamp the
          registry). Application docs render from THIS snapshot.
`check` : (CI) verify the lock hash still matches the registry, regenerate the
          results table and assert the committed copy is unchanged, and scan docs/
          and site/ for result-like numbers that are NOT derivable from the
          registry. Fails if any is found.

The scan targets result-like tokens (decimals and percentages). Structural
constants (limits, budgets, counts, years, plate ids, reference years) are
allowlisted in eval/numbers_allowlist.txt. Every headline rate/CI in the docs is
rendered from the registry, so it is derivable by construction.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "results" / "registry.json"
LOCK = REPO / "results" / "NUMBERS_LOCK.json"
TABLE = REPO / "docs" / "tables" / "results.md"
ALLOWLIST = REPO / "eval" / "numbers_allowlist.txt"
SCAN_FILES = ["docs/POST.md", "docs/FINAL_REPORT.md", "README.md"]
SCAN_GLOBS = ["site/data/*.json"]

_NUM = re.compile(r"\d+\.\d+|\d+%")


def _metrics() -> list:
    return json.loads(REGISTRY.read_text())["metrics"]


def metrics_sha(metrics) -> str:
    canon = json.dumps(sorted(metrics, key=lambda m: m["metric_id"]),
                       sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()


def render_table(metrics) -> str:
    lines = ["# Results table (rendered from results/registry.json; do not edit by hand)",
             "", "| metric | value | 95% CI | n |", "|---|---|---|---|"]
    for m in sorted(metrics, key=lambda x: x["metric_id"]):
        v = m["value"]
        if isinstance(v, list):
            val = f"[curve, {len(v)} points]"
            ci = ""
        else:
            val = f"{v}"
            ci = (f"[{m['ci_lo']}, {m['ci_hi']}]"
                  if m.get("ci_lo") is not None else "")
        lines.append(f"| {m['metric_id']} | {val} | {ci} | {m.get('n', '')} |")
    return "\n".join(lines) + "\n"


def _allowed_strings(metrics) -> set:
    allowed = set()
    for m in metrics:
        vals = []
        if not isinstance(m["value"], list):
            vals.append(m["value"])
        for key in ("ci_lo", "ci_hi"):
            if m.get(key) is not None:
                vals.append(m[key])
        for v in vals:
            if isinstance(v, (int, float)):
                allowed.add(f"{v}")
                allowed.add(f"{round(float(v), 4)}")
                allowed.add(f"{round(float(v), 3)}")
                allowed.add(f"{round(float(v), 2)}")
                allowed.add(f"{round(float(v) * 100, 1)}%")
                allowed.add(f"{round(float(v) * 100)}%")
                allowed.add(f"{round(float(v) * 100, 2)}%")
    return allowed


def _allowlist() -> set:
    if not ALLOWLIST.exists():
        return set()
    return {ln.strip() for ln in ALLOWLIST.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")}


def lock() -> int:
    metrics = _metrics()
    sha = metrics_sha(metrics)
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(render_table(metrics))
    lock_rec = {"registry_sha256": sha, "n_metrics": len(metrics),
                "note": "SPEC numbers lock: docs/site render from this snapshot; a new "
                        "snapshot requires regenerating every doc that cited the first."}
    LOCK.write_text(json.dumps(lock_rec, indent=2) + "\n")
    data = json.loads(REGISTRY.read_text())
    data["numbers_lock"] = lock_rec
    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"NUMBERS LOCK: sha256 {sha[:16]}... n_metrics {len(metrics)} -> {LOCK.name}, {TABLE}")
    return 0


def check() -> int:
    metrics = _metrics()
    ok = True
    if LOCK.exists():
        locked = json.loads(LOCK.read_text())["registry_sha256"]
        if locked != metrics_sha(metrics):
            print("numbers-lock: registry metrics changed since lock (re-run lock).")
            ok = False
    if TABLE.exists() and TABLE.read_text() != render_table(metrics):
        print("numbers-lock: results table out of date (re-run lock).")
        ok = False
    allowed = _allowed_strings(metrics) | _allowlist()
    offenders = []
    files = [REPO / f for f in SCAN_FILES]
    for g in SCAN_GLOBS:
        files += list(REPO.glob(g))
    for f in files:
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            for tok in _NUM.findall(line):
                if tok not in allowed:
                    offenders.append((f.relative_to(REPO).as_posix(), i, tok))
    if offenders:
        ok = False
        print("numbers-lock: result-like numbers not derivable from the registry:")
        for rel, i, tok in offenders[:60]:
            print(f"  {rel}:{i}  {tok}")
    if ok:
        print("numbers-lock: OK (every result-like number renders from the registry).")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        return check()
    return lock()


if __name__ == "__main__":
    raise SystemExit(main())
