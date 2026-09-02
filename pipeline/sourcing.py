"""Stage 1 — Sourcing.

Pull a YC batch from the yc-oss JSON mirror, then best-effort enrich each
company with text from its own homepage (for team/traction signal and, crucially,
a traceable source for later memo claims). Website fetch failures degrade
gracefully: the Startup is still emitted, flagged `site_fetch_ok=False`.
"""
from __future__ import annotations

import json

import httpx
from bs4 import BeautifulSoup

from . import config
from .cache import cached
from .hn import hn_signal, hn_source
from .models import HNSignal, Source, Startup
from .yc_profile import yc_profile

_UA = {"User-Agent": "vc-pipeline/0.1 (take-home; contact via repo)"}


def _fetch_batch(slug: str, use_cache: bool) -> list[dict]:
    url = config.YC_BATCH_URL.format(slug=slug)
    raw = cached(
        "yc-batch",
        url,
        lambda: httpx.get(url, headers=_UA, timeout=20, follow_redirects=True).text,
        use_cache=use_cache,
    )
    # Commit the raw batch pull so reviewers can diff the source of truth.
    (config.RAW / f"yc-{slug}.json").write_text(raw)
    return json.loads(raw)


def _fetch_site_text(url: str, use_cache: bool) -> tuple[str, bool]:
    """Return (trimmed visible text, ok). Never raises."""

    def _do() -> dict:
        try:
            r = httpx.get(
                url, headers=_UA, timeout=config.SITE_FETCH_TIMEOUT, follow_redirects=True
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ").split())
            return {"text": text[: config.SITE_FETCH_MAX_CHARS], "ok": True}
        except Exception as e:  # noqa: BLE001 - degrade gracefully on any fetch error
            return {"text": "", "ok": False, "error": str(e)[:200]}

    res = cached("site", url, _do, use_cache=use_cache)
    return res["text"], res["ok"]


def _to_startup(rec: dict, use_cache: bool, enrich: bool) -> Startup:
    website = rec.get("website") or None
    yc_url = rec.get("url", "")
    sources = [Source(kind="yc", url=yc_url, note="YC company profile")]
    site_text, ok = "", False
    if enrich and website:
        site_text, ok = _fetch_site_text(website, use_cache)
        if ok:
            sources.append(Source(kind="website", url=website, note="Company homepage"))
    # Second source (the thesis-aligned one): YC profile founders -> team-axis signal.
    profile = yc_profile(yc_url, use_cache=use_cache) if enrich else {}
    founders = profile.get("founders", [])
    if founders:
        sources.append(Source(kind="yc-founders", url=yc_url, note=f"{len(founders)} founder profile(s)"))
    if profile.get("launch_text"):
        sources.append(Source(kind="yc-launch", url=yc_url, note="YC Launch post"))
    # Source fusion: cross-reference HN by domain for a real traction/freshness signal.
    hn = hn_signal(website, use_cache=use_cache) if enrich else HNSignal()
    hn_src = hn_source(hn)
    if hn_src:
        sources.append(hn_src)
    return Startup(
        name=rec.get("name", ""),
        slug=rec.get("slug", ""),
        website=website,
        one_liner=rec.get("one_liner", "") or "",
        description=rec.get("long_description", "") or "",
        industry=rec.get("industry", "") or "",
        tags=rec.get("tags", []) or [],
        team_size=rec.get("team_size"),
        year_founded=profile.get("year_founded"),
        location=rec.get("all_locations", "") or "",
        batch=rec.get("batch", "") or "",
        yc_status=rec.get("status", "") or "",
        yc_stage=rec.get("stage", "") or "",
        launched_at=rec.get("launched_at"),
        yc_url=rec.get("url", "") or "",
        site_text=site_text,
        site_fetch_ok=ok,
        founders=founders,
        github_url=profile.get("github_url", "") or "",
        launch_text=profile.get("launch_text", "") or "",
        job_titles=profile.get("job_titles", []) or [],
        hn=hn,
        sources=sources,
    )


def source_batch(
    slug: str = config.DEFAULT_BATCH,
    limit: int = 15,
    *,
    enrich: bool = True,
    use_cache: bool = True,
    industry_filter: str | None = None,
) -> list[Startup]:
    """Collect `limit` candidate startups from a YC batch.

    `industry_filter` (substring, case-insensitive) narrows the batch toward the
    thesis before spending enrichment/LLM budget — e.g. "health", "fintech".
    """
    records = _fetch_batch(slug, use_cache)
    if industry_filter:
        f = industry_filter.lower()
        records = [
            r
            for r in records
            if f in (r.get("industry", "") + " " + r.get("subindustry", "")).lower()
        ]
    records = records[:limit]
    return [_to_startup(r, use_cache, enrich) for r in records]
