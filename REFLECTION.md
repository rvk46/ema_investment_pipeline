# About this doc
This has been drafted by me and refined by claude. This doc will help to understand the flow and process of development.

# Reflection — how I worked with AI

Short version of how I thought about this and where the judgment calls were. I used
Claude Code as a pair: I set direction and made the calls, it wrote most of the code and
ran the checks. What i essentially did was to drive the flow, provide it direction.

## How I approached it

I read the brief once and pulled out the two things that actually get graded: a working
source→analyze→recommend pipeline, and a visible trail of how I worked. So I decided up
front to keep a running `DECISIONS.md` as I went, not write it after. If I couldn't
explain a choice in a line or two, it usually meant I hadn't made the choice yet.

## The calls I made, and why

- **One source, deep.** The brief warns against a 12-source layer that each returns
  garbage. I picked YC W25 and went deep instead of wide.
- **Pull YC from a JSON mirror, not the site.** The live site is JS-rendered and its
  Algolia key rotates — I checked, it 403s. The `yc-oss` mirror is reproducible, which the
  rubric explicitly rewards ("commit the outputs so we don't re-run").
- **Specific thesis.** "Vertical AI agents in regulated back-office." I wanted a thesis
  that would score a great horizontal dev tool *low* on purpose. A thesis that likes
  everything scores nothing.
- **LLM judges, code decides.** The model scores five axes; the weighting and the
  Pass/Watch/Meeting thresholds live in code. I didn't want the verdict to be vibes.

## Where I changed my mind

The most useful moment was the second source. I added Hacker News first because it's free
and gives traction. Then instead of assuming it helped, I measured it: 12.5% coverage,
0% on healthcare/fintech, all hits dev-tools. It was misaligned with my own thesis, and
it gave traction when the axis actually capping my scores was *team*. So I demoted it and
went looking for founder data instead — found it structured inside YC's own page markup.
Coverage went 0/11 → 11/11 and the scores finally moved. Lesson I keep relearning: measure
the thing before you trust it.

## A mistake I caught

After wiring in founders, the team scores were still stuck at 40. I almost accepted it.
When I actually printed the evidence being sent to the model, the founder bios were right
there — the low scores were a stale cached run. A clean `--no-cache` pass fixed it and the
real distribution appeared. Worth the two minutes of not trusting the output.

## Then the failure mode flipped

With good founder data, 55% of companies cleared the meeting bar — too many for a "top
10%" triage. That's when the brief's "top 10%" question clicked: it's a bandwidth budget,
not a fixed number. I added `--budget N` to cap meetings to the top N above the floor.

## Where AI helped vs where I drove

AI was fastest at the mechanical middle — writing modules, tests, and parsers once I'd
decided the shape. I drove the decisions: what to source, the thesis and its weights, when
to stop, and the calls to measure HN and to keep the scoring math out of the prompt. The
one place I had to slow the AI down was verification — it's happy to report success; I made
it print evidence and re-run without cache before I believed a number.

## If I had another day

Add web-search enrichment for founder funding/press (the real quality lever, deferred
because it needs a paid key), and start a feedback loop so partner decisions could learn
the axis weights instead of me hand-setting them. That loop is where a prototype like this
turns into a product.
