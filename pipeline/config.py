"""Central config: thesis weights, scoring thresholds, models, paths.

Kept in one place so the thesis is applied *consistently* across every company
instead of being re-improvised per memo. Reviewers can read the fund's opinion
here in ~30 lines.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
MEMOS = DATA / "memos"
CACHE = ROOT / ".cache"
PROMPTS = ROOT / "prompts"

for _p in (RAW, MEMOS, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# --- Models -------------------------------------------------------------
# Two tiers: a cheap model for nothing yet (reserved), a strong model for the
# structured analysis + memo. Overridable via env for cost experiments.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_MODEL_TRIAGE = os.getenv("OPENAI_MODEL_TRIAGE", "gpt-4o-mini")

# --- Thesis scoring -----------------------------------------------------
# Axis weights MUST sum to 100. The LLM scores each axis 0-100; we combine here
# in code (not in the prompt) so the weighting is auditable and deterministic.
SCORE_WEIGHTS: dict[str, int] = {
    "thesis_fit": 30,
    "team": 20,
    "market_why_now": 20,
    "moat": 15,
    "traction": 15,
}
assert sum(SCORE_WEIGHTS.values()) == 100, "score weights must sum to 100"

# Call thresholds on the final weighted score.
TAKE_MEETING_AT = 70
WATCH_AT = 50  # >= WATCH_AT and < TAKE_MEETING_AT -> Watch; below -> Pass

# --- Sourcing -----------------------------------------------------------
# yc-oss is a community-maintained JSON mirror of the YC company directory.
# Reproducible and key-free, unlike scraping the JS-rendered YC site.
YC_BATCH_URL = "https://yc-oss.github.io/api/batches/{slug}.json"
DEFAULT_BATCH = "winter-2025"

# Website enrichment fetch budget.
SITE_FETCH_TIMEOUT = 12
SITE_FETCH_MAX_CHARS = 6000  # trimmed homepage text handed to the LLM


def require_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise SystemExit(
            "OPENAI_API_KEY not set. Copy .env.example to .env and add your key, "
            "or export OPENAI_API_KEY. Sourcing works without it; analysis/memo do not."
        )
    return key
