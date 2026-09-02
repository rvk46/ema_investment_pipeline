"""Stage 2 — Analysis.

Turn a sourced Startup into a structured, thesis-aligned Analysis. The LLM scores
each axis 0-100 from evidence only; the *weighting* into a final score happens here
in code (deterministic, auditable) rather than in the prompt.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import config
from .llm import complete_json
from .models import Analysis, AxisScore, Source, Startup
from .signals import build_signals

_SYSTEM = (config.PROMPTS / "analysis_system.md").read_text()


def _evidence(s: Startup) -> str:
    launched = (
        datetime.fromtimestamp(s.launched_at, timezone.utc).date().isoformat()
        if s.launched_at
        else "unknown"
    )
    site = s.site_text if s.site_fetch_ok else "(homepage fetch failed / unavailable)"
    if s.founders:
        founders = "\n".join(
            f"- {f.name} — {f.title}: {f.bio or '(no bio)'}"
            + (f" [LinkedIn: {f.linkedin_url}]" if f.linkedin_url else "")
            for f in s.founders
        )
    else:
        founders = "(no founder profiles found — team assessment is low-confidence)"
    launch = s.launch_text or "(no YC Launch post found)"
    jobs = (
        f"{len(s.job_titles)} open role(s): " + ", ".join(s.job_titles)
        if s.job_titles
        else "(no open roles listed)"
    )
    if s.hn.found:
        hn = (
            f"HN presence FOUND: {s.hn.story_count} story(ies), top {s.hn.max_points} points / "
            f"{s.hn.total_comments} comments, Show HN: {s.hn.is_show_hn}, "
            f"most recent {s.hn.most_recent[:10]}. Top: \"{s.hn.top_title}\""
        )
    else:
        hn = "HN presence: none found for this domain (weak external traction signal)."
    return f"""## Company evidence for {s.name}

YC one-liner: {s.one_liner}
YC long description: {s.description}
Industry: {s.industry}
Tags: {", ".join(s.tags) or "none"}
Team size: {s.team_size if s.team_size is not None else "unknown"}
Year founded: {s.year_founded or "unknown"}
Location: {s.location or "unknown"}
Batch: {s.batch}
YC status: {s.yc_status or "unknown"}   YC stage: {s.yc_stage or "unknown"}
Launched (YC): {launched}
Website: {s.website or "unknown"}
GitHub: {s.github_url or "unknown"}

## Founders (YC profile — primary team-axis evidence)
{founders}

## YC Launch post (founders' own description — product / why-now / compliance)
{launch}

## Hiring (open roles — freshness/stage signal)
{jobs}

## Hacker News signal (source fusion — external traction/freshness)
{hn}

## Homepage text (may be truncated)
{site}
"""


def weighted(axes: dict[str, AxisScore]) -> int:
    total = sum(axes[k].score * w for k, w in config.SCORE_WEIGHTS.items())
    return round(total / sum(config.SCORE_WEIGHTS.values()))


def analyze(s: Startup, *, use_cache: bool = True) -> Analysis:
    data = complete_json(
        model=config.OPENAI_MODEL,
        system=_SYSTEM,
        user=_evidence(s),
        use_cache=use_cache,
    )
    axes = {k: AxisScore(**data["axes"][k]) for k in config.SCORE_WEIGHTS}
    gaps = list(data.get("data_gaps", []))
    if not s.site_fetch_ok:
        gaps.append("Homepage text unavailable — analysis based on YC fields only.")
    return Analysis(
        slug=s.slug,
        name=s.name,
        team=data.get("team", ""),
        product=data.get("product", ""),
        market=data.get("market", ""),
        risks=list(data.get("risks", [])),
        open_questions=list(data.get("open_questions", [])),
        axes=axes,
        weighted_score=weighted(axes),
        fatal_risk=bool(data.get("fatal_risk", False)),
        data_gaps=gaps,
        signals=build_signals(s),
        citations=s.sources or [Source(kind="yc", url=s.yc_url)],
        model=config.OPENAI_MODEL,
    )
