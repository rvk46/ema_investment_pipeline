# AI-Augmented VC Triage Pipeline

Source → analyze → recommend. Point it at a YC batch (optionally filtered to a
thesis-relevant industry) and get one skimmable memo per startup, each ending in a
clear **Pass / Watch / Take a meeting** call with traceable sources.

Built for the Emergence take-home. The fund's thesis is deliberately specific — see
[`THESIS.md`](THESIS.md). How this was built (decisions, tradeoffs, AI collaboration)
is logged in [`DECISIONS.md`](DECISIONS.md).

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env        # then paste your OPENAI_API_KEY into .env

# One command, topic-filtered slice of a YC batch, end to end:
pipeline run --industry health --limit 12

# "Top 10%" as a bandwidth budget: surface only the top N as "Take a meeting".
pipeline run --industry health --limit 12 --budget 3
```

`--budget N` ranks candidates and marks only the top N *above the quality floor* as
"Take a meeting" (the rest → Watch). It's a cap, not a quota: a weak batch surfaces fewer
than N rather than promoting junk. Omit it for pure absolute-threshold calls.

Outputs (all committed, so a reviewer never has to re-run):
- `data/startups.json` — stage 1, sourced candidates + evidence
- `data/analysis.json` — stage 2, structured thesis-aligned analysis + scores
- `data/memos/<slug>.md` — stage 3, one-page memo per startup
- `data/memos.json` — memos + calls in one file
- `data/llm_cost.log` — per-call token + spend log

## Design in one paragraph

Three clean stages, each a module (`sourcing`, `analysis`, `recommendation`) reading
the previous stage's committed JSON and writing its own — so the pipeline is
**replayable at any boundary** and you never re-pay for an earlier stage. Every
network + LLM call is **content-hash cached** (`.cache/`), so re-runs are free and
deterministic. The LLM scores five axes 0–100 from evidence only; the **weighting and
the Pass/Watch/Meeting thresholds live in code** (`config.py`), not the prompt, so the
thesis is applied *consistently* and auditably. Missing data (e.g. a JS-rendered
homepage that yields no text) **degrades gracefully**: the company is still analyzed,
with the gap flagged in `data_gaps` and reflected in the memo rather than hallucinated.

## Stages

| Stage | Command | In → Out |
|---|---|---|
| 1. Source | `pipeline source --industry health` | YC batch (yc-oss JSON) + homepage text → `startups.json` |
| 2. Analyze | `pipeline analyze` | `startups.json` → `analysis.json` (LLM, thesis-scored) |
| 3. Recommend | `pipeline memo` | `analysis.json` → `data/memos/*.md` |
| all | `pipeline run` | topic → memos |
| eval | `pipeline evaluate` | `analysis.json` + `eval/labels.json` → discrimination + agreement |

`--no-cache` on any command forces a fresh fetch / model call.

The `run` table is just an index. Full detail per company lives in `data/memos/<slug>.md`
(memo + verified signals + sources) and `data/analysis.json` (axis scores + rationale).
To read one in the terminal — axis breakdown *and* rendered memo:

```bash
pipeline show harper      # per-axis why + data gaps + full memo
```

### Eval

```bash
pipeline evaluate                              # thesis discrimination + call agreement
pipeline evaluate --stability egress-health    # re-run one company 3x, measure wobble
```

A *lite* harness (`eval/labels.json`, 6 hand-labelled companies): checks that `thesis_fit`
cleanly separates on-thesis from off-thesis companies, that calls land in a human-acceptable
set, and that scores are stable across runs. See `DECISIONS.md` (Decision 9) for results.

## Sources

Two sources, both free, key-free, and reproducible:

1. **YC batch** via the [yc-oss](https://github.com/yc-oss/api) JSON mirror — name,
   website, descriptions, team size, industry, YC status (Active/Acquired/…), stage,
   launch date. Reproducible, versus scraping YC's JS-rendered site.
2. **YC company profile** — parsed from the Inertia `data-page` JSON embedded in each
   company's YC page: founders (name, title, **bio**, LinkedIn), `year_founded`,
   `github_url`, the **YC Launch post** (founders' own product / why-now / compliance
   writeup), and **open roles** (hiring signal). This is the signal the batch feed lacks
   and the fund's `team` / `moat` / `market` axes need. Coverage on the test slice:
   founders **11/11**, launch posts **11/11** — all from one already-fetched page, no
   extra requests.

**A note on judgment (see `DECISIONS.md`):** I first added Hacker News as the second
source, then *measured* it — 12.5% coverage overall, 0% on healthcare/fintech, and it
supplies traction when the axis actually capping our scores is `team`. So HN was
**demoted** to a secondary signal and YC founder profiles became the real second source.
Adding founders moved the pipeline from "everything caps at Watch" to a real
Pass/Watch/Meeting distribution. The homepage of each company is also fetched for extra
product/traction context and per-claim source traceability.

## Testing

```bash
pytest
```

Covers the deterministic core — score weighting, the thesis thresholds, and graceful
degradation when a company has no website. The LLM's judgment isn't unit-tested (it's
non-deterministic); the machinery around it is.

## Deliberately deferred (and why)

Scoping is a choice. These are known, valuable, and *not* built — on purpose. Fuller
rationale in `DECISIONS.md`.

| Next step | Why it matters | Why skipped now |
|---|---|---|
| **Agentic web-search enrichment** (founder funding / press cross-check) | Biggest remaining quality lever; would push more companies past the meeting bar on real evidence | Needs a paid search API key (Brave/Serp) → new dependency, not reproducible for a reviewer without the key. Clean insertion point exists (analysis evidence step). |
| **Multi-source + entity resolution** (Crunchbase, PH, GitHub) | Broader coverage than one YC batch | Each new source needs dedup / entity resolution to avoid the "12 sources × 2 garbage results" anti-pattern. Not worth it for a one-batch triage prototype. |
| **Learned scoring weights + feedback loop** | THE lever for a real product: learn axis weights from partner decisions instead of hand-setting them | No labelled outcome data yet. Hand-set thesis weights are the honest v1; learning on zero data would be theatre. |
| **Claim-span provenance / NLI entailment** | Verify each memo sentence entails from evidence | The deterministic **Verified signals** block already covers the high-value provenance need; span-level NLI is diminishing returns at the triage layer. |
| **Orchestration / incremental ingestion** (scheduling, alerting) | Continuous deal flow vs one-shot batch | Explicitly out of scope per the brief ("no job queue"). CLI + committed files is right for this stage. |

## Cost

`data/llm_cost.log` records tokens + estimated USD per call. Caching means a re-run of
an unchanged batch costs $0. Full build to date: ~$0.85.
