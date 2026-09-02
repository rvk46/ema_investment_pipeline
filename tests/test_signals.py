"""Tests for the deterministic provenance layer: verified facts + their sources."""
from pipeline.models import Founder, HNSignal, Startup
from pipeline.signals import build_signals


def _startup(**kw) -> Startup:
    base = dict(name="Acme", slug="acme", yc_url="https://yc/acme")
    base.update(kw)
    return Startup(**base)


def test_signals_tag_founders_to_yc_founders_source():
    s = _startup(founders=[Founder(name="Jane Doe", title="CEO")], year_founded=2024)
    sigs = {x.label: x for x in build_signals(s)}
    fk = next(k for k in sigs if k.startswith("Founders"))
    assert sigs[fk].source_kind == "yc-founders"
    assert "Jane Doe" in sigs[fk].value
    assert sigs["Year founded"].value == "2024"


def test_signals_include_hn_only_when_found():
    without = build_signals(_startup(website="https://acme.io"))
    assert not any(x.label == "HN traction" for x in without)
    with_hn = build_signals(
        _startup(website="https://acme.io", hn=HNSignal(found=True, max_points=120, total_comments=40))
    )
    hn = next(x for x in with_hn if x.label == "HN traction")
    assert hn.source_kind == "hn" and "120 pts" in hn.value


def test_signals_skip_empty_values():
    sigs = build_signals(_startup())  # no team_size, no founders, no website
    labels = {x.label for x in sigs}
    assert "Team size" not in labels and not any(l.startswith("Founders") for l in labels)
