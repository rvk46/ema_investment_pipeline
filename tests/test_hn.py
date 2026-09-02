"""Tests for the HN source-fusion layer: domain parsing + exact-match filtering."""
from pipeline.hn import registrable_domain
from pipeline.models import HNSignal


def test_registrable_domain_strips_scheme_and_www():
    assert registrable_domain("https://www.cursor.com/pricing") == "cursor.com"
    assert registrable_domain("http://tryegress.com") == "tryegress.com"
    assert registrable_domain("acme.io") == "acme.io"
    assert registrable_domain("") == ""


def test_hn_signal_defaults_are_safe():
    s = HNSignal()
    assert s.found is False and s.max_points == 0 and s.domain == ""


def test_exact_domain_filter_logic():
    # Mimic the filter in hn_signal: fuzzy Algolia hits, keep only exact-domain matches.
    domain = "cursor.com"
    hits = [
        {"url": "https://cursor.com/changelog", "points": 600},
        {"url": "https://snyk.io/blog/cursor-com-review", "points": 574},  # fuzzy noise
        {"url": "https://www.cursor.com/en/blog", "points": 120},
    ]
    kept = [h for h in hits if registrable_domain(h["url"]) == domain]
    assert len(kept) == 2  # snyk.io dropped
    assert max(h["points"] for h in kept) == 600
