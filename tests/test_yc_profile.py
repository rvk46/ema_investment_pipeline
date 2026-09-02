"""Tests for the YC-profile founder parser (the thesis-aligned second source).

Uses a minimal synthetic Inertia `data-page` blob so the parser is tested without
a network call — same HTML-entity-encoded shape YC serves.
"""
import html as htmllib
import json

from pipeline.yc_profile import _parse


def _fixture(company: dict, launches: list | None = None, jobs: list | None = None) -> str:
    props = {"company": company, "launches": launches or [], "jobPostings": jobs or []}
    blob = htmllib.escape(json.dumps({"props": props}))
    return f'<div id="app" data-page="{blob}" >content</div>'


def test_parse_extracts_founders_and_extras():
    html = _fixture(
        {
            "year_founded": 2024,
            "github_url": "https://github.com/acme",
            "founders": [
                {
                    "full_name": "Jane Doe",
                    "title": "Founder/CEO",
                    "founder_bio": "2nd time founder, ex-Stripe.",
                    "linkedin_url": "https://linkedin.com/in/janedoe",
                    "twitter_url": "",
                }
            ],
        }
    )
    out = _parse(html)
    assert out["year_founded"] == 2024
    assert out["github_url"] == "https://github.com/acme"
    assert len(out["founders"]) == 1
    f = out["founders"][0]
    assert f.name == "Jane Doe" and f.title == "Founder/CEO"
    assert "ex-Stripe" in f.bio


def test_parse_missing_data_page_degrades():
    out = _parse("<html><body>no data-page here</body></html>")
    assert out["founders"] == [] and out["year_founded"] is None


def test_parse_no_founders_key():
    out = _parse(_fixture({"year_founded": 2025}))
    assert out["founders"] == [] and out["year_founded"] == 2025


def test_parse_extracts_launch_and_jobs():
    out = _parse(
        _fixture(
            {"year_founded": 2025},
            launches=[{"title": "Acme launches", "body": "HIPAA-compliant AI for X."}],
            jobs=[{"title": "Founding Engineer"}, {"title": ""}],  # blank dropped
        )
    )
    assert "HIPAA-compliant" in out["launch_text"]
    assert out["job_titles"] == ["Founding Engineer"]


def test_parse_absent_launch_and_jobs_are_empty():
    out = _parse(_fixture({"year_founded": 2025}))
    assert out["launch_text"] == "" and out["job_titles"] == []
