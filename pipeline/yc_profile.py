"""Second source (the one that matters) — YC company profile founder data.

The yc-oss batch feed has no founders, and founders are the signal our thesis's
`team` axis actually needs. YC's own company page embeds a full structured company
object (founders with name/title/bio/LinkedIn, plus year_founded, github_url) in an
Inertia.js `data-page` attribute in the initial HTML — no JS execution required.

We parse that blob. This beats scraping /about /team pages, which SPAs defeat
(every path returns the same shell). Free, key-free, reproducible.
"""
from __future__ import annotations

import html as htmllib
import json
import re

import httpx

from .cache import cached
from .models import Founder

_UA = {"User-Agent": "Mozilla/5.0 vc-pipeline/0.1 (take-home)"}
_DATA_PAGE = re.compile(r'data-page="(.*?)"\s*>', re.S)


class YCProfile(dict):
    """Thin holder: {'founders': [Founder...], 'year_founded': int|None, 'github_url': str}."""


def _fetch_html(yc_url: str, use_cache: bool) -> str:
    def _do() -> str:
        try:
            r = httpx.get(yc_url, headers=_UA, timeout=15, follow_redirects=True)
            r.raise_for_status()
            return r.text
        except Exception:  # noqa: BLE001 - profile fetch must not break sourcing
            return ""

    return cached("yc-profile-html", yc_url, _do, use_cache=use_cache)


# The Launch YC post is often the single richest evidence blob (product + why-now +
# compliance, in the founders' words). Trim it to keep token cost bounded.
_LAUNCH_MAX_CHARS = 2500

_EMPTY = {
    "founders": [],
    "year_founded": None,
    "github_url": "",
    "launch_text": "",
    "job_titles": [],
}


def _parse(html_text: str) -> dict:
    m = _DATA_PAGE.search(html_text)
    if not m:
        return dict(_EMPTY)
    try:
        data = json.loads(htmllib.unescape(m.group(1)))
        props = data.get("props", {}) or {}
        company = props.get("company", {}) or {}
    except (json.JSONDecodeError, AttributeError):
        return dict(_EMPTY)

    founders = [
        Founder(
            name=f.get("full_name", "") or "",
            title=f.get("title", "") or "",
            bio=(f.get("founder_bio", "") or "").strip(),
            linkedin_url=f.get("linkedin_url", "") or "",
            twitter_url=f.get("twitter_url", "") or "",
        )
        for f in (company.get("founders") or [])
    ]

    # Launch YC posts (title + body markdown), concatenated and trimmed.
    launch_parts = []
    for lp in props.get("launches") or []:
        title = (lp.get("title") or "").strip()
        body = (lp.get("body") or "").strip()
        if title or body:
            launch_parts.append(f"{title}\n{body}".strip())
    launch_text = "\n\n---\n\n".join(launch_parts)[:_LAUNCH_MAX_CHARS]

    job_titles = [
        (j.get("title") or "").strip()
        for j in (props.get("jobPostings") or [])
        if (j.get("title") or "").strip()
    ]

    return {
        "founders": founders,
        "year_founded": company.get("year_founded"),
        "github_url": company.get("github_url", "") or "",
        "launch_text": launch_text,
        "job_titles": job_titles,
    }


def yc_profile(yc_url: str, *, use_cache: bool = True) -> dict:
    """Return founders + year_founded + github_url + launch_text + job_titles for a YC URL.

    Never raises; returns empty values on any failure so sourcing degrades cleanly.
    """
    if not yc_url:
        return dict(_EMPTY)
    return _parse(_fetch_html(yc_url, use_cache))
