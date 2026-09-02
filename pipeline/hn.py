"""Second source — Hacker News (Algolia API), used for signal fusion.

Not a separate candidate list: HN is cross-referenced against each YC company by
its website domain to attach a real *traction + freshness* signal (points,
comments, Show HN, recency). This is the signal the YC feed lacks and the reason
every company was capping at "Watch".

Free, key-free. Algolia's `query` is fuzzy (matches title text too), so we fetch
candidates and keep only hits whose URL is an exact registrable-domain match.
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

from .cache import cached
from .models import HNSignal, Source

_UA = {"User-Agent": "vc-pipeline/0.1 (take-home)"}
_API = "https://hn.algolia.com/api/v1/search"


def registrable_domain(url: str) -> str:
    """Naive but adequate: netloc minus www. 'https://www.cursor.com/x' -> 'cursor.com'."""
    if not url:
        return ""
    netloc = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    return netloc.removeprefix("www.")


def _search(domain: str, use_cache: bool) -> list[dict]:
    def _do() -> list[dict]:
        try:
            r = httpx.get(
                _API,
                params={
                    "query": domain,
                    "restrictSearchableAttributes": "url",
                    "tags": "story",
                    "hitsPerPage": 30,
                },
                headers=_UA,
                timeout=12,
            )
            r.raise_for_status()
            return r.json().get("hits", [])
        except Exception:  # noqa: BLE001 - HN outage must not break sourcing
            return []

    return cached("hn", domain, _do, use_cache=use_cache)


def hn_signal(website: str | None, *, use_cache: bool = True) -> HNSignal:
    """Aggregate HN traction for a company's domain. Empty signal if no match."""
    domain = registrable_domain(website or "")
    if not domain:
        return HNSignal(domain="", found=False)

    # Keep only hits that actually point at this domain (drop fuzzy title matches).
    hits = [h for h in _search(domain, use_cache) if registrable_domain(h.get("url", "")) == domain]
    if not hits:
        return HNSignal(domain=domain, found=False)

    hits.sort(key=lambda h: h.get("points") or 0, reverse=True)
    top = hits[0]
    is_show_hn = any((h.get("title") or "").lower().startswith("show hn") for h in hits)
    most_recent = max((h.get("created_at") or "") for h in hits)
    return HNSignal(
        domain=domain,
        found=True,
        story_count=len(hits),
        max_points=top.get("points") or 0,
        total_points=sum(h.get("points") or 0 for h in hits),
        total_comments=sum(h.get("num_comments") or 0 for h in hits),
        is_show_hn=is_show_hn,
        top_title=(top.get("title") or "")[:200],
        top_url=f"https://news.ycombinator.com/item?id={top.get('objectID')}",
        most_recent=most_recent,
    )


def hn_source(sig: HNSignal) -> Source | None:
    if not sig.found:
        return None
    return Source(kind="hn", url=sig.top_url, note=f"HN: {sig.max_points} pts, {sig.total_comments} comments")
