"""Tests for the lite eval metrics (offline — synthetic analyses, no LLM/network)."""
from pipeline import config
from pipeline.evaluate import call_agreement, thesis_discrimination
from pipeline.models import Analysis, AxisScore, Source


def _analysis(slug, thesis_fit, weighted):
    axes = {k: AxisScore(score=(thesis_fit if k == "thesis_fit" else 50), rationale="x")
            for k in config.SCORE_WEIGHTS}
    return Analysis(slug=slug, name=slug, team="", product="", market="", risks=[],
                    open_questions=[], axes=axes, weighted_score=weighted,
                    citations=[Source(kind="yc", url="u")])


def test_thesis_discrimination_detects_clean_separation():
    labels = [{"slug": "hi", "thesis": "high"}, {"slug": "lo", "thesis": "low"}]
    byslug = {"hi": _analysis("hi", 90, 70), "lo": _analysis("lo", 20, 40)}
    d = thesis_discrimination(labels, byslug)
    assert d["cleanly_separated"] is True
    assert d["margin"] == 70.0


def test_thesis_discrimination_flags_overlap():
    labels = [{"slug": "hi", "thesis": "high"}, {"slug": "lo", "thesis": "low"}]
    byslug = {"hi": _analysis("hi", 40, 55), "lo": _analysis("lo", 50, 45)}  # overlap
    d = thesis_discrimination(labels, byslug)
    assert d["cleanly_separated"] is False


def test_call_agreement_scores_against_acceptable_sets():
    labels = [
        {"slug": "meet", "acceptable_calls": ["Take a meeting", "Watch"]},
        {"slug": "pass", "acceptable_calls": ["Pass"]},
    ]
    byslug = {"meet": _analysis("meet", 80, 75), "pass": _analysis("pass", 20, 30)}
    ca = call_agreement(labels, byslug)
    assert ca["agreement"] == 1.0 and ca["n"] == 2
