"""The one wrapper for all LLM calls (P6.1; pattern from refs pipeline/llm.py).

No baseline or attacker calls a provider SDK directly. Features:
  * Keys: read from $WS/.env via python-dotenv INTO THE PROCESS ONLY (never
    exported to the shell; an exported ANTHROPIC_API_KEY would change how Claude
    Code itself is billed). The LABGATE_ prefix keeps billing to the owner's keys.
  * Cache: key = sha256 of canonical JSON of the full request
    {provider, model, system, messages, temperature, max_tokens, replicate_tag}.
    A cache hit returns with NO network call, which is what lets `make demo`
    reproduce headline numbers from cache without keys (P9.9).
  * Meter: tokens + USD per call aggregated per role into logs/cost_meter.json,
    checked against config/budget.yaml and $WS/.env LLM_BUDGET_USD (R-08). A
    projected overflow raises BudgetExceeded; no further spend.
  * No keys, cache miss: raises LLMKeysMissing. We NEVER fabricate a response.
  * JSON robustness: strip ``` fences for callers expecting JSON.

With both keys as placeholders (D-020) every real call raises LLMKeysMissing; the
cache and meter machinery is still exercised offline via `call(..., _stub=...)` in
tests. The LLM gate and attacker catch LLMKeysMissing and defer, disclosed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parent.parent
WS = REPO.parent
CACHE_DIR = REPO / "eval" / "cache"
METER = WS / "logs" / "cost_meter.json"
BUDGET_YAML = REPO / "config" / "budget.yaml"
ENV_FILE = WS / ".env"

# USD per 1e6 tokens (input, output); meter only (budget guardrail is the hard cap).
# Pinned models (R-13, verified live 2026-11-03): gpt-5.1, claude-opus-5-5.
PRICING = {
    "gpt-5.1": {"in": 1.25, "out": 10.0},
    "gpt-5": {"in": 1.25, "out": 10.0},
    "claude-opus-5-5": {"in": 5.0, "out": 25.0},
    "claude-sonnet-5-5": {"in": 3.0, "out": 15.0},
    "stub-model": {"in": 0.0, "out": 0.0},
}


class LLMKeysMissing(RuntimeError):
    """No cached response and the vendor key is a placeholder/absent (D-020)."""


class BudgetExceeded(RuntimeError):
    """The per-role cap or the total LLM budget would be exceeded (R-08)."""


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _key_for(provider: str) -> Optional[str]:
    env = _load_env()
    name = {"openai": "LABGATE_OPENAI_API_KEY",
            "anthropic": "LABGATE_ANTHROPIC_API_KEY"}.get(provider)
    val = env.get(name, "")
    if not val or val == "replace-me":
        return None
    return val


def provider_of(model: str) -> str:
    m = model.lower()
    if m.startswith("gpt") or m.startswith("o"):
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    return "stub" if m.startswith("stub") else "unknown"


def strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.lstrip().lower().startswith("json"):
            t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _request_hash(req: dict) -> str:
    canon = json.dumps(req, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()


def _load_meter() -> dict:
    if METER.exists():
        return json.loads(METER.read_text())
    return {"total_usd": 0.0, "by_role": {}, "calls": 0}


def _save_meter(m: dict) -> None:
    METER.parent.mkdir(parents=True, exist_ok=True)
    METER.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def _budget() -> dict:
    import yaml
    b = yaml.safe_load(BUDGET_YAML.read_text()) if BUDGET_YAML.exists() else {}
    env = _load_env()
    total = float(env.get("LLM_BUDGET_USD", b.get("total_usd_default", 500)))
    return {"total": total, "hard_cap": float(b.get("hard_cap_usd", total)),
            "per_role": b.get("per_role_usd", {})}


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    p = PRICING.get(model, {"in": 0.0, "out": 0.0})
    return in_tok / 1e6 * p["in"] + out_tok / 1e6 * p["out"]


def call(role: str, model: str, system: str, messages: list[dict], *,
         max_tokens: int = 1024, temperature: float = 0.0,
         replicate_tag: str = "r0", _stub: Optional[Callable[[dict], dict]] = None) -> dict:
    """Return {text, provider, model, cache_source, usage}. Cache-first.

    ``_stub`` (tests only) stands in for the provider SDK so the cache/meter path is
    exercised offline. In production the stub is None: a cache miss with no key
    raises LLMKeysMissing (we never fabricate).
    """
    provider = provider_of(model)
    req = {"provider": provider, "model": model, "system": system,
           "messages": messages, "max_tokens": max_tokens,
           "temperature": temperature, "replicate_tag": replicate_tag}
    h = _request_hash(req)
    cache_path = CACHE_DIR / f"{h}.json"
    if cache_path.exists():
        rec = json.loads(cache_path.read_text())
        rec["cache_source"] = "disk"
        return rec

    # budget check (projected)
    budget = _budget()
    meter = _load_meter()
    if meter["total_usd"] >= budget["hard_cap"]:
        raise BudgetExceeded(f"total spend {meter['total_usd']:.2f} >= cap {budget['hard_cap']}")
    role_cap = budget["per_role"].get(role)
    if role_cap is not None and meter["by_role"].get(role, 0.0) >= role_cap:
        raise BudgetExceeded(f"role {role} spend >= cap {role_cap}")

    if _stub is not None:
        resp = _stub(req)                 # offline test path
    else:
        key = _key_for(provider)
        if key is None:
            raise LLMKeysMissing(
                f"no cached response for this request and {provider} key is a "
                f"placeholder; set $WS/.env (see OWNER_TODO.md). No fabrication.")
        resp = _provider_call(provider, key, req)   # real network path

    in_tok = resp.get("usage", {}).get("input_tokens", 0)
    out_tok = resp.get("usage", {}).get("output_tokens", 0)
    cost = _cost(model, in_tok, out_tok)
    meter["total_usd"] = round(meter["total_usd"] + cost, 6)
    meter["by_role"][role] = round(meter["by_role"].get(role, 0.0) + cost, 6)
    meter["calls"] += 1
    _save_meter(meter)

    rec = {"text": resp["text"], "provider": provider, "model": model,
           "cache_source": "live", "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
           "cost_usd": cost, "replicate_tag": replicate_tag}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    return rec


def _provider_call(provider: str, key: str, req: dict) -> dict:  # pragma: no cover
    """Real SDK call. Only reached when a key is present (never in this build)."""
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=req["model"], system=req["system"], messages=req["messages"],
            max_tokens=req["max_tokens"], temperature=req["temperature"])
        return {"text": msg.content[0].text,
                "usage": {"input_tokens": msg.usage.input_tokens,
                          "output_tokens": msg.usage.output_tokens}}
    if provider == "openai":
        import openai
        client = openai.OpenAI(api_key=key)
        kwargs = dict(model=req["model"],
                      messages=[{"role": "system", "content": req["system"]}] + req["messages"])
        m = req["model"].lower()
        # gpt-5 / o-series reasoning models use max_completion_tokens and only the
        # default temperature; older models use max_tokens + temperature.
        if m.startswith("gpt-5") or m.startswith("o"):
            kwargs["max_completion_tokens"] = max(req["max_tokens"], 2048)
        else:
            kwargs["max_tokens"] = req["max_tokens"]
            kwargs["temperature"] = req["temperature"]
        r = client.chat.completions.create(**kwargs)
        return {"text": r.choices[0].message.content or "",
                "usage": {"input_tokens": r.usage.prompt_tokens,
                          "output_tokens": r.usage.completion_tokens}}
    raise LLMKeysMissing(f"unknown provider {provider}")
