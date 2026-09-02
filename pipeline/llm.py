"""Thin OpenAI wrapper: cached, retried, cost-logged JSON completions.

One choke point for every model call so caching, retries, and spend tracking are
uniform and auditable. Returns parsed dicts; callers validate into pydantic.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from . import config
from .cache import cached

_client: OpenAI | None = None

# Rough USD per 1M tokens (input, output) for spend estimation only.
_PRICES = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.require_openai_key())
    return _client


def _log_cost(model: str, usage) -> None:
    pin, pout = _PRICES.get(model, (0.0, 0.0))
    cost = (usage.prompt_tokens * pin + usage.completion_tokens * pout) / 1_000_000
    line = (
        f"{datetime.now(timezone.utc).isoformat()}\t{model}\t"
        f"in={usage.prompt_tokens}\tout={usage.completion_tokens}\t${cost:.4f}\n"
    )
    with open(config.ROOT / "data" / "llm_cost.log", "a") as f:
        f.write(line)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
def _call(model: str, system: str, user: str) -> str:
    resp = _get_client().chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    if resp.usage:
        _log_cost(model, resp.usage)
    return resp.choices[0].message.content or "{}"


def complete_json(
    *, model: str, system: str, user: str, use_cache: bool = True
) -> dict:
    """Cached JSON completion. Cache key covers model+system+user, so editing a
    prompt naturally invalidates just the affected calls."""
    payload = json.dumps({"m": model, "s": system, "u": user}, sort_keys=True)
    raw = cached(
        "llm", payload, lambda: _call(model, system, user), use_cache=use_cache
    )
    return json.loads(raw)
