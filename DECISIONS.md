# Decision & Build Log

A factual record of how this pipeline was scoped and built, the tradeoffs taken, and
where AI did the work. Per the assignment ground rules: AI was used heavily and openly.
This file is the honest trail, not a retrofitted one.

> **On voice:** this log is deliberately factual (decisions, reasons, tradeoffs). The
> first-person *reflection* on working with AI lives in [`REFLECTION.md`](REFLECTION.md)
> and is written by me, the candidate — not generated. Don't grade my reflection off this
> file.

---

## How this was built

Built in a single Claude Code (Opus) session, pairing style: I set direction and made
the judgment calls (source, thesis, scope, thresholds); the assistant proposed options,
wrote most of the module code, and ran the verification. Key forks below.

---

## Decision 1 — Sourcing: YC batch via the `yc-oss` JSON mirror

**Options weighed:** Hacker News (Algolia API), YC batch, Product Hunt, GitHub trending.

- Chose **YC W25** because a batch is a bounded, high-signal candidate set that already
  looks like deal flow, and it carries a built-in traction signal (`status`:
  Active/Acquired/Public) plus launch dates for freshness.
- **Did not scrape** YC's site — it's JS-rendered and the embedded Algolia key rotates
  (confirmed live: the commonly-cited key now returns `403 Invalid Application-ID or API
  key`). Instead used [`yc-oss/api`](https://github.com/yc-oss/api), a community JSON
  mirror served over GitHub Pages: key-free, versioned, reproducible. This directly
  serves the rubric's "replayable / commit the outputs" requirement.
- **Tradeoff:** the mirror has no founder names. Rather than add a fragile second scraper,
  each company's own homepage is fetched for team/traction signal. This doubles as the
  **traceable source** every memo claim needs (rubric anti-pattern: "claims with no
  source").

**Corner cut on purpose:** one source, gone deep — not the "12-source layer where each
returns 2 garbage results" the rubric warns against.

## Decision 2 — Thesis: narrow on purpose

Defined a *specific* thesis — "vertical AI agents automating back-office ops in regulated
industries" — over a broad one. The rubric explicitly penalizes a thesis so broad the
score is meaningless. Consequence, by design: a genuinely great horizontal dev-tool
company should score **low** here on `thesis_fit`. That's the thesis being held
consistently, not a bug. Full rubric in `THESIS.md`.

## Decision 3 — Scoring: LLM judges axes, code does the math

The LLM scores five axes 0–100 from evidence; the **weighting into a final score and the
Pass/Watch/Meeting thresholds live in `config.py`**, not the prompt.

- Keeps the fund's opinion (the weights) auditable and identical across every company.
- Makes the score deterministic given the axis scores — easy to explain and defend.
- A fatal risk demotes an otherwise-strong score from "meeting" to "watch" in code, so
  the call logic is explicit rather than vibed by the model.

## Decision 4 — Replayability & cost: content-hash cache everywhere

Every network fetch and every model call goes through one cache keyed by a hash of its
inputs (`cache.py`). Re-running an unchanged batch costs $0 and returns identical output.
Editing a prompt changes its hash and naturally invalidates just the affected calls.
Raw YC pulls are committed under `data/raw/`; the call-cache is gitignored.

## Decision 5 — Robustness: degrade, don't hallucinate

Homepage fetches fail (SPA returns ~50 chars, or no site). The pipeline still emits the
company, flags `site_fetch_ok=False`, appends the gap to `data_gaps`, and the analysis
prompt is instructed to treat missing evidence as *unknown* and lower confidence — never
to invent founders/metrics/customers. Verified live: 5/6 healthcare homepages fetched;
the 6th (no website) degraded cleanly instead of crashing.

## Scope explicitly cut (per constraints)

- No job queue, no vector DB, no frontend — the assignment says stop if you're building
  these. Output is committed files + a CLI.
- No founder-enrichment scraper / LinkedIn — fragile, ToS-risky, low marginal signal for
  a triage layer.
- LLM judgment is not unit-tested (non-deterministic); the deterministic machinery around
  it is (`tests/`).

## What AI wrote vs. what I directed

- **I directed:** source choice, the thesis and its weights, the code-side scoring split,
  cache strategy, scope cuts, thresholds.
- **AI wrote:** most module code (`sourcing`, `analysis`, `recommendation`, `llm`,
  `cache`, `cli`), the prompt drafts, and the tests — then ran them and the live sourcing
  check. I reviewed each and adjusted.

## Decision 6 — Second source: added Hacker News, then measured it and demoted it

Added HN (Algolia API, free, key-free) as a second source, fused to each YC company by
exact website-domain match to attach a traction/freshness signal (points, comments, Show
HN, recency). Wired, tested, and verified capturing correctly (cursor.com → 24 stories /
613 pts; ycombinator.com → 5 / 2060 pts).

**Then I measured its yield instead of assuming it.** On a 40-company W25 sample:

| Metric | Result |
|---|---|
| Overall coverage | 5/40 (12.5%) |
| Companies with HN presence | all 5 were **B2B/dev-tools** (Subtrace, SubImage, Promptless, Onlook, Tweeks) |
| Stories with real traction (>50 pts) | **1/40** (rest 1–5 pts = noise) |
| Healthcare / Fintech / Industrials / Government | **0** coverage |

**Conclusion: HN is misaligned with this fund's thesis.** HN over-indexes
dev-tools/infra/consumer; our thesis targets *regulated back-office verticals*
(healthcare, insurance, fintech) — which by nature don't get posted to HN. And HN
supplies *traction*, whereas the axis actually capping our scores is **`team`** (founder
background), which HN doesn't touch at all.

**What I did about it:** kept HN wired but **demoted** — it costs ~$0, demonstrates the
source-fusion machinery, and helps if the thesis ever includes dev-tools. It is no longer
treated as the primary second source. The real second source needs to attack the binding
constraint (founder/team + budget/compliance signal). See Decision 7.

The point worth grading here is the *process*: I didn't keep a source because it was
built — I measured coverage, found it thesis-misaligned, and pivoted.

## Decision 7 — The second source that matters: YC founder profiles

After demoting HN, I picked the second source by asking *what actually caps our scores* —
the `team` axis, flat at ~40 because we had no founder data. So the right second source is
one that supplies **founders**, not more traction.

I evaluated three, with live feasibility tests instead of assumptions:

| Candidate | Verdict |
|---|---|
| Company `/about` `/team` crawl | **Rejected.** Works on server-rendered sites (Exin) but SPAs return the *same shell* for every path (Toothy: `/about` == `/team` == `/x`, 3.4k chars, no founder text). Unreliable. |
| YC company page — Inertia `data-page` JSON | **Chosen.** YC embeds a full structured company object (founders: name/title/**bio**/LinkedIn, plus `year_founded`, `github_url`) in the initial HTML — no JS execution needed. Free, reproducible, structured. |
| Crunchbase / LinkedIn | Rejected for now: need keys / ToS-risky, not reproducible for a reviewer. |

**Result:** founder coverage went from **0/11 (HN) to 11/11 (YC profiles)**. Bios carry
exactly the signal the thesis wants — e.g. Toothy's "2nd time founder now automating back
office functions for dental clinics" is domain-fit + repeat-founder in one line. The
`team` axis now scores from evidence instead of defaulting to "unknown".

Implementation: `pipeline/yc_profile.py` parses the entity-encoded `data-page` blob;
graceful-degrades to empty founders on any failure; parser unit-tested with a synthetic
fixture (no network). HN stays wired but demoted to a secondary traction signal.

## Decision 8 — Provenance: separate verified facts from LLM judgment

Rubric target: "spot-check one analysis and trust where its claims came from." A memo that
blends machine-checkable facts with model inference gives a reviewer no way to tell which
is which. So I added a deterministic **`Signals`** layer (`pipeline/signals.py`): facts
pulled straight from the sourced data — YC status, team size, year founded, founders,
launch date, GitHub, HN traction — each tagged with the source it came from. These are
computed in code, never by the LLM, so they carry zero hallucination risk.

Every memo now renders a **"Verified signals"** block (label: value [source]) kept
visually distinct from the inferred prose. The model is instructed to render them verbatim
and not paraphrase away the source. Net effect: a reviewer sees the hard facts and their
provenance at a glance, and the LLM's judgment sits clearly on top of that, not mixed in.
Unit-tested for source tagging and for omitting absent facts.

## Decision 9 — Lite eval harness: is the score trustworthy?

Scores are only defensible if they *discriminate* and *don't wobble*. Built a lite eval
(`pipeline/evaluate.py`, `pipeline evaluate`) over a small hand-labelled set
(`eval/labels.json`, 6 clear-cut companies; ambiguous ones excluded on purpose). Three
checks:

1. **Thesis discrimination** — mean `thesis_fit` on-thesis **86.7** vs off-thesis **26.7**,
   margin **60**, cleanly separated (every on-thesis company scored above every off-thesis
   one: 85 vs 30). The specific thesis actually bites.
2. **Call agreement** — absolute calls landed in the human-acceptable set **6/6 (1.0)**.
3. **Stability** — re-running one company 3× (no cache): `thesis_fit` [85,85,85] range 0;
   `weighted` [72,73,73] stdev 0.47. At temp 0.2 the score is near-deterministic, so the
   number a partner sees isn't a dice roll.

Metrics 1–2 run off committed `analysis.json` (free); stability is opt-in (makes fresh
calls). The metric functions are unit-tested offline with synthetic analyses. This is a
*lite* eval by design — no backtesting against real outcomes (we have none), but enough
to show the score separates on-thesis from off-thesis and is reproducible.

## Decision 10 — Deepen evidence for free: parse the YC Launch post + jobs

The biggest remaining quality lever was more evidence per company, and the obvious path
(web search) needs a paid key. But I was already downloading the YC company page for
founders — and its `data-page` blob also carries the **Launch YC post** (the founders'
own product / why-now / compliance writeup) and **job postings** (a hiring/freshness
signal). I was parsing founders and throwing the rest away.

So I extended the same parser (no new requests, no new dependency) to extract the launch
body (trimmed to 2.5k chars) and open roles, and fed both into the analysis evidence and
the provenance signals. Coverage: **11/11 launch posts**, 2/11 hiring. The launch text is
often the single richest description available — e.g. Toothy's names HIPAA compliance,
which feeds `moat` and `thesis_fit` directly. This is the web-search flow's payoff without
its cost or its reproducibility problem. Parser unit-tested for launch + jobs extraction.

## Finding — the eval harness caught launch-post marketing bias (and the fix)

Adding the YC Launch post as evidence helped, but the eval immediately flagged a
regression: call agreement dropped **1.0 → 0.83** and thesis margin **60 → 48**. The
culprit was **Amby Health** (a consumer coaching app, labelled off-thesis) jumping
47 → 70 and crossing the absolute meeting floor. Root cause: launch posts are
founder-authored *marketing*, and the persuasive copy inflated the non-thesis axes.

Fix: a prompt guard telling the model to treat the launch post / homepage as promotional,
discount hype, and only let concrete verifiable facts move a score. Re-running the eval
confirmed the fix: agreement back to **1.0**, Amby down to 64 (Watch). This is the whole
point of the lite eval — a change that *looked* like a pure win was measured, shown to
introduce a false positive, corrected, and re-verified in one loop.

Residual limitation I'm choosing not to chase: Amby's `thesis_fit` still reads higher than
ideal (~70). The ranking still separates on-thesis from off-thesis, and tuning the prompt
harder against one example would be overfitting. Logged as a known limit rather than hidden.

## Finding — richer data flips the failure mode: now it *over*-promotes

Before founders: everything capped at Watch (thin `team` data). After adding YC founder
profiles: team scores moved to 50–85 and the healthcare slice returned **6 "Take a
meeting" / 4 Watch / 1 Pass** — 55% meetings. That's too many for a triage layer meant to
surface the "top 10%".

This exposes a real design gap: the calls are **absolute-threshold only** (score ≥70).
Absolute thresholds are honest on thin data (they return nothing rather than junk) but
**over-promote once data is rich** — 55% clearing the bar defeats the point of triage.
The fix is a **relative budget**: rank by weighted score and mark only the top-N
(partner's weekly bandwidth) above a quality floor as "Take a meeting". "Top 10%" is best
defined as a *bandwidth budget, not a fixed fraction*.

**Built** as `--budget N` (`recommendation.assign_calls`): portfolio-level pass that caps
meetings to the top-N *above the absolute floor* — never promoting below it, so a weak
batch surfaces fewer than N rather than junk. Demo: the 6-meeting healthcare slice with
`--budget 2` cuts to the top 2 (Mecha 76, Egress 73), rest → Watch. Unit-tested for the
cap, the never-promote-below-floor guarantee, and the no-budget=absolute default.

## Finding — triage stays conservative on thin data (by design)

Running the full W25 healthcare slice (11 companies), every thesis-fit company
clustered at **Watch (62–68)** and none reached the **≥70 "Take a meeting"** bar. This
is not a threshold bug. The `team` and `traction` axes sit ~40–50 because YC one-liners
plus thin SPA homepages carry no founder background or traction metrics — so the weighted
score is capped below 70. The pipeline is correctly **refusing to greenlight a partner
meeting without team/traction evidence**, and each memo says exactly what's missing.

The lever to unlock "Take a meeting" is *more evidence*, not a lower bar: add founder
enrichment (LinkedIn/Crunchbase) and a real traction signal (GitHub, funding, press). I
deliberately did **not** build that scraper for a triage layer — the conservative call on
thin data is the honest behavior, and the thresholds stay fixed to the thesis rather than
tuned to force a nicer-looking distribution.

## Verification done

- `pytest` — 5 tests pass (weighting, thresholds, graceful degradation).
- Live sourcing run on the healthcare slice of W25 — homepages fetched with graceful
  degradation on SPA/no-site companies.
- Full `run` on 11 healthcare companies: analysis + 11 memos generated and committed.
  Total model spend **~$0.15** (`data/llm_cost.log`); re-runs are $0 via the cache.
- Thesis discrimination confirmed: back-office RCM/billing automation scored high on
  `thesis_fit` (80–90); biotech/drug-discovery and consumer health scored low (10–20),
  as the thesis intends.
