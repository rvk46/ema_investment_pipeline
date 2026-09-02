"""Stage 3 — Recommendation.

Decide the call from the score (in code, so it's consistent with the thesis
thresholds), then have the LLM write a memo consistent with that decided call.
The model does not get to re-score or overturn the verdict.
"""
from __future__ import annotations

import json

from . import config
from .llm import complete_json
from .models import Analysis, Call, Memo

_SYSTEM = (config.PROMPTS / "memo_system.md").read_text()


def decide_call(analysis: Analysis) -> Call:
    """Absolute-threshold call for a single company (no budget)."""
    score = analysis.weighted_score
    if score >= config.TAKE_MEETING_AT and not analysis.fatal_risk:
        return "Take a meeting"
    # A strong score undercut by a fatal risk lands in Watch, not a meeting.
    if score >= config.WATCH_AT or (score >= config.TAKE_MEETING_AT and analysis.fatal_risk):
        return "Watch"
    return "Pass"


def assign_calls(analyses: list[Analysis], *, budget: int | None = None) -> dict[str, Call]:
    """Portfolio-level call assignment.

    Without a budget: pure absolute thresholds (`decide_call`).

    With a budget: "top 10%" is treated as a *bandwidth budget, not a fixed fraction*.
    We rank the meeting-eligible companies (those that clear the absolute floor with no
    fatal risk) by score and keep only the top `budget` as "Take a meeting"; the rest are
    demoted to "Watch". The budget only *caps* — it never promotes a company below the
    quality floor, so a weak batch surfaces fewer than `budget` rather than junk.
    """
    calls: dict[str, Call] = {a.slug: decide_call(a) for a in analyses}
    if budget is None:
        return calls
    eligible = sorted(
        (a for a in analyses if calls[a.slug] == "Take a meeting"),
        key=lambda a: a.weighted_score,
        reverse=True,
    )
    for a in eligible[budget:]:  # everyone past the budget cut -> Watch
        calls[a.slug] = "Watch"
    return calls


def _brief(a: Analysis, call: Call) -> str:
    payload = {
        "name": a.name,
        "decided_call": call,
        "weighted_score": a.weighted_score,
        "team": a.team,
        "product": a.product,
        "market": a.market,
        "risks": a.risks,
        "open_questions": a.open_questions,
        "axis_scores": {k: {"score": v.score, "why": v.rationale} for k, v in a.axes.items()},
        "fatal_risk": a.fatal_risk,
        "data_gaps": a.data_gaps,
        "verified_signals": [
            {"label": s.label, "value": s.value, "source": s.source_kind, "url": s.source_url}
            for s in a.signals
        ],
        "sources": [s.url for s in a.citations if s.url],
    }
    return json.dumps(payload, indent=2)


def recommend(a: Analysis, *, call: Call | None = None, use_cache: bool = True) -> Memo:
    if call is None:
        call = decide_call(a)
    data = complete_json(
        model=config.OPENAI_MODEL,
        system=_SYSTEM,
        user=_brief(a, call),
        use_cache=use_cache,
    )
    return Memo(
        slug=a.slug,
        name=a.name,
        call=call,
        weighted_score=a.weighted_score,
        memo_markdown=data.get("memo_markdown", ""),
        change_my_mind=list(data.get("change_my_mind", [])),
        model=config.OPENAI_MODEL,
    )
