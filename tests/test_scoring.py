"""Tests for the deterministic core: weighting and the call decision.

The LLM's judgment is not unit-tested (non-deterministic), but the parts that
must be *consistent* across every company — the weighted score and the
thesis thresholds that pick Pass/Watch/Meeting — are.
"""
from pipeline import config
from pipeline.analysis import weighted
from pipeline.models import Analysis, AxisScore, Source
from pipeline.recommendation import assign_calls, decide_call
from pipeline.sourcing import _to_startup


def _axes(**scores):
    return {k: AxisScore(score=scores.get(k, 0), rationale="x") for k in config.SCORE_WEIGHTS}


def _analysis(score, fatal=False, slug="s"):
    axes = {k: AxisScore(score=score, rationale="x") for k in config.SCORE_WEIGHTS}
    return Analysis(
        slug=slug, name=slug, team="", product="", market="", risks=[],
        open_questions=[], axes=axes, weighted_score=score, fatal_risk=fatal,
        citations=[Source(kind="yc", url="u")],
    )


def test_weighted_all_equal_returns_same():
    assert weighted(_axes(**{k: 80 for k in config.SCORE_WEIGHTS})) == 80


def test_weighted_respects_thesis_fit_weight():
    # thesis_fit (weight 30) high, everything else 0 -> 30% of 100 = 30
    a = _axes(thesis_fit=100)
    assert weighted(a) == 30


def test_decide_meeting_needs_score_and_no_fatal_risk():
    assert decide_call(_analysis(75)) == "Take a meeting"
    assert decide_call(_analysis(75, fatal=True)) == "Watch"  # fatal risk demotes


def test_decide_watch_and_pass_bands():
    assert decide_call(_analysis(60)) == "Watch"
    assert decide_call(_analysis(config.WATCH_AT)) == "Watch"
    assert decide_call(_analysis(config.WATCH_AT - 1)) == "Pass"


def test_budget_caps_meetings_to_top_n():
    # four clear the floor (>=70); budget of 2 keeps only the top two as meetings.
    xs = [_analysis(s, slug=f"c{s}") for s in (85, 80, 75, 72, 60, 40)]
    calls = assign_calls(xs, budget=2)
    meetings = [slug for slug, c in calls.items() if c == "Take a meeting"]
    assert meetings == ["c85", "c80"]  # top 2 by score
    assert calls["c75"] == "Watch" and calls["c72"] == "Watch"  # demoted, not promoted-over
    assert calls["c60"] == "Watch" and calls["c40"] == "Pass"  # bands unchanged below floor


def test_budget_never_promotes_below_floor():
    # weak batch: only one clears the floor; budget of 5 still surfaces just that one.
    xs = [_analysis(s, slug=f"c{s}") for s in (72, 55, 50, 30)]
    calls = assign_calls(xs, budget=5)
    assert sum(c == "Take a meeting" for c in calls.values()) == 1


def test_no_budget_is_pure_absolute():
    xs = [_analysis(s, slug=f"c{s}") for s in (85, 80, 75)]
    calls = assign_calls(xs, budget=None)
    assert all(c == "Take a meeting" for c in calls.values())


def test_sourcing_maps_fields_and_degrades_without_website():
    rec = {
        "name": "Acme", "slug": "acme", "one_liner": "does things",
        "long_description": "long", "industry": "Healthcare", "team_size": 3,
        "status": "Active", "url": "https://ycombinator.com/companies/acme",
        "website": None,
    }
    s = _to_startup(rec, use_cache=True, enrich=True)
    assert s.name == "Acme" and s.team_size == 3
    assert s.site_fetch_ok is False  # no website -> graceful, no crash
    assert any(src.kind == "yc" for src in s.sources)
