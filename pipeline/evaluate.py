"""Lite eval harness — is the score trustworthy?

Not a full ML eval. Three cheap, defensible checks against a small hand-labelled set
(`eval/labels.json`):

1. Thesis discrimination — does the `thesis_fit` axis actually separate on-thesis from
   off-thesis companies? (The whole point of a *specific* thesis.)
2. Call agreement — does the absolute call land in the set a human labeller would accept?
3. Stability — re-run one company N times; how much does the score wobble? (LLM = noisy.)

Checks 1–2 read the already-committed analysis.json (free). Check 3 makes fresh
no-cache calls, so it is opt-in.
"""
from __future__ import annotations

import json
import statistics

from . import config
from .analysis import analyze
from .models import Analysis, Startup
from .recommendation import decide_call

LABELS = config.ROOT / "eval" / "labels.json"


def _load_labels() -> list[dict]:
    return json.loads(LABELS.read_text())["labels"]


def _analyses_by_slug() -> dict[str, Analysis]:
    data = json.loads((config.DATA / "analysis.json").read_text())
    return {a["slug"]: Analysis(**a) for a in data}


def thesis_discrimination(labels: list[dict], byslug: dict[str, Analysis]) -> dict:
    hi = [byslug[l["slug"]].axes["thesis_fit"].score for l in labels if l["thesis"] == "high" and l["slug"] in byslug]
    lo = [byslug[l["slug"]].axes["thesis_fit"].score for l in labels if l["thesis"] == "low" and l["slug"] in byslug]
    mean_hi = round(statistics.mean(hi), 1) if hi else None
    mean_lo = round(statistics.mean(lo), 1) if lo else None
    separated = bool(hi and lo and min(hi) > max(lo))  # every on-thesis beats every off-thesis
    return {
        "mean_thesis_fit_high": mean_hi,
        "mean_thesis_fit_low": mean_lo,
        "margin": round(mean_hi - mean_lo, 1) if (mean_hi is not None and mean_lo is not None) else None,
        "cleanly_separated": separated,
        "min_high": min(hi) if hi else None,
        "max_low": max(lo) if lo else None,
    }


def call_agreement(labels: list[dict], byslug: dict[str, Analysis]) -> dict:
    rows, hits = [], 0
    for l in labels:
        a = byslug.get(l["slug"])
        if not a:
            continue
        got = decide_call(a)
        ok = got in l["acceptable_calls"]
        hits += ok
        rows.append({"slug": l["slug"], "call": got, "acceptable": l["acceptable_calls"], "ok": ok})
    n = len(rows)
    return {"agreement": round(hits / n, 2) if n else None, "n": n, "rows": rows}


def stability(slug: str, runs: int = 3) -> dict:
    """Re-analyze one company `runs` times (no cache) and report score spread."""
    startups = {s["slug"]: Startup(**s) for s in json.loads((config.DATA / "startups.json").read_text())}
    s = startups[slug]
    fits, weighted = [], []
    for _ in range(runs):
        a = analyze(s, use_cache=False)
        fits.append(a.axes["thesis_fit"].score)
        weighted.append(a.weighted_score)
    return {
        "slug": slug,
        "runs": runs,
        "thesis_fit": {"values": fits, "range": max(fits) - min(fits), "stdev": round(statistics.pstdev(fits), 2)},
        "weighted": {"values": weighted, "range": max(weighted) - min(weighted), "stdev": round(statistics.pstdev(weighted), 2)},
    }


def run_eval() -> dict:
    labels = _load_labels()
    byslug = _analyses_by_slug()
    report = {
        "thesis_discrimination": thesis_discrimination(labels, byslug),
        "call_agreement": call_agreement(labels, byslug),
    }
    (config.DATA / "eval_report.json").write_text(json.dumps(report, indent=2))
    return report
