"""Deterministic signal extraction — the provenance layer.

Turns the sourced facts into a list of `Signal`s, each tagged with the source it
came from. These are *verified facts*, not LLM claims: a reviewer can trust them
without re-deriving. Memos render them in a separate "Verified signals" block so
machine-checkable facts are visibly distinct from the model's inferred judgment.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .models import Signal, Startup


def build_signals(s: Startup) -> list[Signal]:
    yc = s.yc_url
    out: list[Signal] = []

    def add(label: str, value: str | None, kind: str, url: str = "") -> None:
        if value:
            out.append(Signal(label=label, value=str(value), source_kind=kind, source_url=url))

    add("YC batch", s.batch, "yc", yc)
    add("YC status", s.yc_status, "yc", yc)
    add("YC stage", s.yc_stage, "yc", yc)
    add("Team size", s.team_size, "yc", yc)
    add("Year founded", s.year_founded, "yc-founders", yc)
    if s.launched_at:
        d = datetime.fromtimestamp(s.launched_at, timezone.utc).date().isoformat()
        add("Launched (YC)", d, "yc", yc)

    if s.founders:
        names = "; ".join(
            f"{f.name} ({f.title})" if f.title else f.name
            for f in s.founders
            if f.name
        )
        add(f"Founders ({len(s.founders)})", names, "yc-founders", yc)
    add("GitHub", s.github_url, "yc-founders", s.github_url)
    if s.job_titles:
        add(f"Hiring ({len(s.job_titles)} open)", "; ".join(s.job_titles), "yc-launch", yc)
    if s.launch_text:
        add("YC Launch post", "present", "yc-launch", yc)
    add("Website", s.website, "website", s.website or "")

    if s.hn.found:
        add(
            "HN traction",
            f"{s.hn.max_points} pts / {s.hn.total_comments} comments"
            + (" (Show HN)" if s.hn.is_show_hn else ""),
            "hn",
            s.hn.top_url,
        )
    return out
