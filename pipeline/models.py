"""Typed data contracts passed between stages.

Each stage reads the previous stage's committed JSON and emits its own, so the
pipeline is replayable at any boundary (source -> analyze -> recommend).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Call = Literal["Pass", "Watch", "Take a meeting"]


class Source(BaseModel):
    """A traceable evidence pointer. Every memo claim should trace to one of these."""

    kind: str  # "yc" | "website" | ...
    url: str
    note: str = ""


class Founder(BaseModel):
    """A founder pulled from the YC company profile — the core `team`-axis signal."""

    name: str = ""
    title: str = ""
    bio: str = ""
    linkedin_url: str = ""
    twitter_url: str = ""


class HNSignal(BaseModel):
    """Hacker News traction/freshness for a company domain (source-fusion signal)."""

    domain: str = ""
    found: bool = False
    story_count: int = 0
    max_points: int = 0
    total_points: int = 0
    total_comments: int = 0
    is_show_hn: bool = False
    top_title: str = ""
    top_url: str = ""
    most_recent: str = ""  # ISO timestamp of most recent story


class Startup(BaseModel):
    """Stage 1 output: a sourced candidate with freshness/traction signal."""

    name: str
    slug: str
    website: str | None = None
    one_liner: str = ""
    description: str = ""
    industry: str = ""
    tags: list[str] = Field(default_factory=list)
    team_size: int | None = None
    year_founded: int | None = None
    location: str = ""
    batch: str = ""
    yc_status: str = ""  # Active / Acquired / Public / Inactive
    yc_stage: str = ""
    launched_at: int | None = None  # unix ts
    yc_url: str = ""
    # Enrichment (best-effort; may be empty if the site fetch failed).
    site_text: str = ""
    site_fetch_ok: bool = False
    founders: list[Founder] = Field(default_factory=list)  # 2nd source: YC profile (team axis)
    github_url: str = ""
    launch_text: str = ""  # YC Launch post (product / why-now / compliance, founders' words)
    job_titles: list[str] = Field(default_factory=list)  # open roles = hiring/freshness signal
    hn: HNSignal = Field(default_factory=HNSignal)  # demoted signal: HN traction
    sources: list[Source] = Field(default_factory=list)


class Signal(BaseModel):
    """A machine-verified fact with its source. Not LLM output — deterministic, so a
    reviewer can trust it without re-deriving. Kept separate from inferred prose."""

    label: str
    value: str
    source_kind: str  # yc | yc-founders | website | hn
    source_url: str = ""


class AxisScore(BaseModel):
    score: int = Field(ge=0, le=100)
    rationale: str


class Analysis(BaseModel):
    """Stage 2 output: structured, thesis-aligned analysis + weighted score."""

    slug: str
    name: str
    team: str
    product: str
    market: str
    risks: list[str]
    open_questions: list[str]
    axes: dict[str, AxisScore]  # keys == config.SCORE_WEIGHTS keys
    weighted_score: int = Field(ge=0, le=100)
    fatal_risk: bool = False
    data_gaps: list[str] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)  # verified facts (provenance)
    citations: list[Source] = Field(default_factory=list)
    model: str = ""
    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Memo(BaseModel):
    """Stage 3 output: the one-page partner-facing recommendation."""

    slug: str
    name: str
    call: Call
    weighted_score: int
    memo_markdown: str
    change_my_mind: list[str]  # 2-3 things that would flip the call
    model: str = ""
