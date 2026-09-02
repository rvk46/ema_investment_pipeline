# Investment Thesis

> **Vertical AI agents that automate labor-intensive back-office operations in regulated industries.**

We are a seed fund. We back software that *replaces labor*, not software that helps
labor. The wedge we like right now: AI agents that own a painful, repetitive,
compliance-heavy back-office workflow end-to-end inside one vertical.

## What we score UP

| Signal | Why it matters to us |
|---|---|
| **AI-native** — the product cannot exist without recent model capability | Timing / "why now". Not an AI feature bolted onto legacy SaaS. |
| **Narrow vertical wedge** — one industry, one workflow | Beachhead beats horizontal. "RCM for dentists" > "AI for ops". |
| **Replaces headcount with measurable ROI** — dollars or FTEs saved | Clear buyer, clear budget, fast sales cycle. |
| **Regulated / compliance-heavy domain** (healthcare, insurance, legal, accounting, logistics) | Willingness to pay + a moat that thin wrappers can't cross. |
| **SMB → mid-market GTM** | Reachable buyers, self-serve or short cycle, capital-efficient. |

## What we score DOWN

- **Horizontal dev tools / infra** — great companies, wrong fund thesis.
- **Consumer / social** — not our edge.
- **Thin GPT wrappers** — no data moat, no workflow depth, easily cloned.
- **No identifiable buyer** — "everyone" is nobody.
- **Research / model labs** — capital intensity we can't lead.

## Scoring rubric (0–100)

The score is a weighted sum of five thesis-aligned axes. Weights encode what
*this fund* cares about — a fantastic horizontal dev tool should still score
mediocre here, on purpose. See `pipeline/config.py` for the exact weights.

| Axis | Weight | 0 | 100 |
|---|---|---|---|
| Thesis fit | 30 | horizontal / consumer / wrapper | vertical AI agent in regulated back-office |
| Team | 20 | no signal / first-time generic | domain + technical depth, prior exits |
| Market & "why now" | 20 | no timing story, tiny/unclear TAM | clear why-now, real budget, expanding |
| Moat / defensibility | 15 | cloneable in a weekend | data / integration / compliance moat |
| Traction & freshness | 15 | stale, no signal | recent launch, revenue/logo/acquisition signal |

## Calls

- **Take a meeting** — score ≥ 70 **and** no fatal risk flagged.
- **Watch** — score 50–69, or high score with one unresolved fatal risk.
- **Pass** — score < 50.

Thresholds live in `pipeline/config.py` so they are held consistently across every
memo, not vibed per-company.
