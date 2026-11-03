"""Static results site generator (P9.3).

Reads results/registry.json (+ a sample of receipts/counterexamples) and writes
site/index.html with ALL data inlined as a JSON blob and the headline chart drawn
as inline SVG. No backend, no external network calls at runtime, no CDN. Light and
dark mode via prefers-color-scheme. Re-run after `make eval` + numbers lock.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "results" / "registry.json"
DATA_DIR = REPO / "site" / "data"
OUT = REPO / "site" / "index.html"


def _load():
    reg = json.loads(REGISTRY.read_text())
    metrics = {m["metric_id"]: m for m in reg["metrics"]}
    return reg, metrics


def _sample_receipts(n=25):
    path = REPO / "results" / "receipts.jsonl"
    out = []
    if path.exists():
        for line in path.read_text().splitlines()[:5000]:
            try:
                r = json.loads(line)
            except Exception:
                continue
            # never surface quarantined free text on the site
            r.pop("quarantined_text", None)
            out.append(r)
    # keep a spread of decisions
    blocks = [r for r in out if r["decision"] == "BLOCK"][:n]
    passes = [r for r in out if r["decision"] == "PASS"][:n]
    abst = [r for r in out if r["decision"] == "ABSTAIN"][:n]
    return (blocks + passes + abst)[: n]


def build() -> str:
    reg, metrics = _load()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def val(mid):
        m = metrics.get(mid)
        return m["value"] if m else None

    gates = ["typed", "classifier", "llm", "llm_parity"]
    scoreboard = []
    for g in gates:
        row = {"gate": g,
               "attack_static_decomp": metrics.get(f"attack.{g}.static_decomp"),
               "attack_adaptive": metrics.get(f"attack.{g}.adaptive"),
               "falseblock_benign": metrics.get(f"falseblock.{g}.benign"),
               "abstain_benign": metrics.get(f"abstain.{g}.benign"),
               "falseblock_surprise": metrics.get(f"falseblock.{g}.surprise"),
               "variance": metrics.get(f"variance.{g}.flip_rate")}
        scoreboard.append(row)
    curves = {g: val(f"attack_curve.{g}") for g in gates if val(f"attack_curve.{g}")}
    receipts = _sample_receipts()

    abstain_bd = metrics.get("abstain_breakdown.typed", {})
    data = {"numbers_lock": reg.get("numbers_lock"), "scoreboard": scoreboard,
            "curves": curves, "receipts": receipts,
            "abstain_breakdown": abstain_bd,
            "checker": {k: val(k) for k in
                        ("equivalence.reference_vs_smt", "replay.counterexample_validity",
                         "latency.p50_ms", "latency.p95_ms", "taint.sentinel_channel",
                         "spec_coverage.out_of_spec_reached", "llm.spend_usd")}}
    (DATA_DIR / "site.json").write_text(json.dumps(data, indent=2) + "\n")

    OUT.write_text(_html(data))
    return str(OUT)


def _svg_curve(curves: dict) -> str:
    # inline SVG line chart: attack success vs attacker budget, one line per gate
    W, H, pad = 640, 320, 48
    colors = {"typed": "#2563eb", "classifier": "#d97706", "llm": "#dc2626"}
    all_b = sorted({p["budget"] for c in curves.values() for p in c}) or [1]
    bmax = max(all_b)
    def x(b):
        return pad + (W - 2 * pad) * (b / bmax if bmax else 0)
    def y(v):
        return H - pad - (H - 2 * pad) * max(0.0, min(1.0, v))
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Attack success vs attacker budget">']
    # axes
    parts.append(f'<line x1="{pad}" y1="{H-pad}" x2="{W-pad}" y2="{H-pad}" class="axis"/>')
    parts.append(f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{H-pad}" class="axis"/>')
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        yy = y(frac)
        parts.append(f'<line x1="{pad}" y1="{yy:.1f}" x2="{W-pad}" y2="{yy:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad-8}" y="{yy+4:.1f}" class="tick" text-anchor="end">{int(frac*100)}%</text>')
    parts.append(f'<text x="{W/2}" y="{H-8}" class="lbl" text-anchor="middle">attacker budget (queries)</text>')
    parts.append(f'<text x="14" y="{H/2}" class="lbl" transform="rotate(-90 14 {H/2})" text-anchor="middle">attack success</text>')
    for g, c in curves.items():
        pts = " ".join(f"{x(p['budget']):.1f},{y(p['value']):.1f}" for p in c)
        col = colors.get(g, "#555")
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"/>')
        # CI band (light) as a thin area between ci_lo and ci_hi
        band = (" ".join(f"{x(p['budget']):.1f},{y(p['ci_hi']):.1f}" for p in c)
                + " " + " ".join(f"{x(p['budget']):.1f},{y(p['ci_lo']):.1f}" for p in reversed(c)))
        parts.append(f'<polygon points="{band}" fill="{col}" opacity="0.12"/>')
    # legend
    lx = W - pad - 150
    for i, (g, _) in enumerate(curves.items()):
        yy = pad + 8 + i * 18
        parts.append(f'<rect x="{lx}" y="{yy-9}" width="12" height="12" fill="{colors.get(g,"#555")}"/>')
        parts.append(f'<text x="{lx+18}" y="{yy+1}" class="tick">{g} gate</text>')
    parts.append("</svg>")
    return "".join(parts)


def _fmt(m):
    if not m:
        return "n/a"
    if isinstance(m, dict):
        v = m.get("value")
        if v is None:
            return "n/a"
        ci = (f" [{m['ci_lo']:.3f}, {m['ci_hi']:.3f}]"
              if m.get("ci_lo") is not None else "")
        n = f" (n={m['n']})" if m.get("n") else ""
        return f"{v:.3f}{ci}{n}"
    return str(m)


def _html(data) -> str:
    rows = ""
    for r in data["scoreboard"]:
        rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(r["gate"]), _fmt(r["attack_static_decomp"]), _fmt(r["attack_adaptive"]),
            _fmt(r["falseblock_benign"]), _fmt(r["abstain_benign"]), _fmt(r["variance"])))
    receipts_rows = ""
    for r in data["receipts"][:30]:
        receipts_rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(str(r.get("decision"))), html.escape(str(r.get("reason", ""))[:60]),
            html.escape(str(r.get("detail", "") or "")), html.escape(str(r.get("plan_hash", ""))[:12])))
    chart = _svg_curve(data["curves"]) if data["curves"] else "<p>No curve data.</p>"
    bd = data.get("abstain_breakdown") or {}
    bd_val = bd.get("value") if isinstance(bd, dict) and "value" in bd else bd
    if isinstance(bd_val, dict) and any(bd_val.values()):
        items = ", ".join(f"{k}={v}" for k, v in bd_val.items() if v)
        abstain_html = (f'<p class="sub">Typed-gate ABSTAIN breakdown by reason '
                        f'(benign stream + attack suites): {html.escape(items)}.</p>')
    else:
        abstain_html = '<p class="sub">Typed-gate ABSTAIN breakdown: none on the benign stream.</p>'
    ck = data["checker"]
    blob = json.dumps(data)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lab-gate results</title>
<style>
:root{{--bg:#fff;--fg:#111;--mut:#555;--card:#f6f7f9;--line:#e3e6ea;--axis:#888;--grid:#eee}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0e1116;--fg:#e8eaed;--mut:#9aa0a6;--card:#171b21;--line:#2a2f37;--axis:#667;--grid:#20242b}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
.wrap{{max-width:900px;margin:0 auto;padding:24px}}h1{{font-size:1.7rem}}h2{{margin-top:2rem}}
.sub{{color:var(--mut)}}table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}}
th,td{{border:1px solid var(--line);padding:6px 8px;text-align:left}}th{{background:var(--card)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}}
.scroll{{overflow-x:auto}}.axis{{stroke:var(--axis)}}.grid{{stroke:var(--grid)}}
.tick{{fill:var(--mut);font-size:11px}}.lbl{{fill:var(--mut);font-size:12px}}
.kpi{{display:flex;flex-wrap:wrap;gap:12px}}.kpi div{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px}}
.kpi b{{display:block;font-size:1.3rem}}code{{background:var(--card);padding:1px 5px;border-radius:4px}}
</style></head><body><div class="wrap">
<h1>lab-gate results</h1>
<p class="sub">A plan-checking safety gate for autonomous labs, built on public helao-async
and evaluated inside its OER simulator. Every number renders from a locked results
registry. Three ways to judge this: watch the demo, read this page, reproduce from cache.</p>

<h2>Headline: attack success vs attacker budget</h2>
<div class="card scroll">{chart}
<p class="sub">Attack success = the gate PASSES a plan the oracle observes to violate
the target rule. Bands are bootstrap 95% CIs. Lower is safer.</p></div>

<h2>Scoreboard</h2>
<div class="card scroll"><table>
<tr><th>gate</th><th>attack success (static+decomp)</th><th>attack success (adaptive)</th>
<th>false-block (benign)</th><th>abstain (benign)</th><th>run-to-run variance</th></tr>
{rows}</table>
<p class="sub">Values are rates with 95% CI and n. Two LLM-gate arms are shown: the
plain gate and the information-parity gate that additionally receives the predicted
potential the typed gate's I1 uses. Surprise-subset false-block is reported too (the
gate must not police novelty).</p>
{abstain_html}</div>

<h2>Checker guarantees</h2>
<div class="kpi">
<div>reference vs SMT<b>{ck.get('equivalence.reference_vs_smt')}</b></div>
<div>counterexample replay<b>{ck.get('replay.counterexample_validity')}</b></div>
<div>taint channel<b>{ck.get('taint.sentinel_channel')}</b></div>
<div>latency p95 (ms)<b>{ck.get('latency.p95_ms')}</b></div>
<div>out-of-spec reached<b>{ck.get('spec_coverage.out_of_spec_reached')}</b></div>
<div>LLM spend (USD)<b>{ck.get('llm.spend_usd')}</b></div>
</div>

<h2>Receipts (sample)</h2>
<div class="card scroll"><table>
<tr><th>verdict</th><th>reason</th><th>rule</th><th>plan hash</th></tr>
{receipts_rows}</table>
<p class="sub">Quarantined free text is never shown here (or read by the checker).</p></div>

<h2>Human checkpoints</h2>
<div class="card"><p>The gate works with human reviewers, not instead of them:
H1 policy sign-off, H2 abstain queue, H3 upstream approval, H4 overrides,
H5 sampled PASS audit, H6 release review. See HUMAN_CHECKPOINTS.md.</p></div>

<p class="sub">Numbers lock: <code>{html.escape(str((data.get('numbers_lock') or {}).get('registry_sha256',''))[:16])}…</code>.
AI-assisted build (Claude Code from a spec written with Claude; owner reviewed the decisions).</p>
<script type="application/json" id="labgate-data">{html.escape(blob)}</script>
</div></body></html>
"""


if __name__ == "__main__":
    print(build())
