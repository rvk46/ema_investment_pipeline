"""CLI — the partner-facing entrypoint.

`pipeline run --industry health` sources a slice of a YC batch, analyzes each
company against the thesis, and writes one memo per startup. Each stage also
exists as its own command and reads/writes committed JSON, so the pipeline is
replayable at any boundary without re-running earlier (paid) stages.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import config
from .analysis import analyze
from .evaluate import run_eval, stability
from .models import Analysis, Memo, Startup
from .recommendation import assign_calls, recommend
from .sourcing import source_batch

app = typer.Typer(add_completion=False, help="AI-augmented VC triage pipeline.")
console = Console()

STARTUPS_JSON = config.DATA / "startups.json"
ANALYSIS_JSON = config.DATA / "analysis.json"
MEMOS_JSON = config.DATA / "memos.json"


def _dump(path: Path, items: list) -> None:
    path.write_text(json.dumps([i.model_dump() for i in items], indent=2))


def _load(path: Path, model) -> list:
    return [model(**d) for d in json.loads(path.read_text())]


@app.command()
def source(
    batch: str = config.DEFAULT_BATCH,
    limit: int = 15,
    industry: str = typer.Option(None, help="Substring filter, e.g. 'health'."),
    enrich: bool = typer.Option(True, help="Fetch company homepages for signal."),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Stage 1: collect candidate startups from a YC batch."""
    startups = source_batch(
        batch, limit, enrich=enrich, use_cache=not no_cache, industry_filter=industry
    )
    _dump(STARTUPS_JSON, startups)
    ok = sum(s.site_fetch_ok for s in startups)
    console.print(
        f"[green]Sourced {len(startups)}[/] from {batch}"
        f"{f' (industry~{industry!r})' if industry else ''} · "
        f"homepages fetched {ok}/{len(startups)} -> {STARTUPS_JSON.name}"
    )


@app.command(name="analyze")
def analyze_cmd(no_cache: bool = typer.Option(False, "--no-cache")):
    """Stage 2: score each sourced startup against the thesis."""
    startups = _load(STARTUPS_JSON, Startup)
    analyses: list[Analysis] = []
    for s in startups:
        console.print(f"  analyzing [cyan]{s.name}[/] …")
        analyses.append(analyze(s, use_cache=not no_cache))
    _dump(ANALYSIS_JSON, analyses)
    console.print(f"[green]Analyzed {len(analyses)}[/] -> {ANALYSIS_JSON.name}")


_BUDGET_OPT = typer.Option(
    None,
    "--budget",
    help="Bandwidth cap: mark only the top-N above the floor as 'Take a meeting'. "
    "This is the defensible 'top 10%'. Omit for pure absolute thresholds.",
)


def _write_memos(analyses: list[Analysis], budget: int | None, no_cache: bool) -> list[Memo]:
    calls = assign_calls(analyses, budget=budget)
    memos: list[Memo] = []
    for a in analyses:
        m = recommend(a, call=calls[a.slug], use_cache=not no_cache)
        memos.append(m)
        (config.MEMOS / f"{m.slug}.md").write_text(m.memo_markdown.rstrip() + "\n")
    _dump(MEMOS_JSON, memos)
    return memos


@app.command()
def memo(
    budget: int = _BUDGET_OPT,
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Stage 3: write one markdown memo per startup + a summary table."""
    analyses = _load(ANALYSIS_JSON, Analysis)
    memos = _write_memos(analyses, budget, no_cache)
    _summary(memos, budget)
    console.print(
        f"[green]Wrote {len(memos)} memos[/] -> {config.MEMOS.relative_to(config.ROOT)}/"
    )


@app.command()
def run(
    batch: str = config.DEFAULT_BATCH,
    limit: int = 15,
    industry: str = typer.Option(None, help="Substring filter, e.g. 'health'."),
    budget: int = _BUDGET_OPT,
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Full pipeline: source -> analyze -> memo, one command."""
    startups = source_batch(
        batch, limit, use_cache=not no_cache, industry_filter=industry
    )
    _dump(STARTUPS_JSON, startups)
    console.print(f"[green]Sourced {len(startups)}[/] from {batch}.")

    analyses = [analyze(s, use_cache=not no_cache) for s in startups]
    _dump(ANALYSIS_JSON, analyses)
    console.print(f"[green]Analyzed {len(analyses)}.[/]")

    memos = _write_memos(analyses, budget, no_cache)
    _summary(memos, budget)


@app.command()
def evaluate(
    stability_slug: str = typer.Option(None, "--stability", help="Re-run one slug N times to measure score wobble."),
    runs: int = typer.Option(3, help="Runs for --stability."),
):
    """Lite eval: thesis discrimination + call agreement vs eval/labels.json."""
    report = run_eval()
    td = report["thesis_discrimination"]
    ca = report["call_agreement"]

    t = Table(title="Thesis discrimination (does thesis_fit separate on/off-thesis?)")
    t.add_column("metric"); t.add_column("value")
    t.add_row("mean thesis_fit — on-thesis", str(td["mean_thesis_fit_high"]))
    t.add_row("mean thesis_fit — off-thesis", str(td["mean_thesis_fit_low"]))
    t.add_row("margin", str(td["margin"]))
    t.add_row("cleanly separated (min_high > max_low)",
              f"[{'green' if td['cleanly_separated'] else 'red'}]{td['cleanly_separated']}[/] "
              f"({td['min_high']} vs {td['max_low']})")
    console.print(t)

    t2 = Table(title=f"Call agreement vs hand labels: {ca['agreement']} ({ca['n']} labelled)")
    t2.add_column("company"); t2.add_column("call"); t2.add_column("acceptable"); t2.add_column("ok")
    for r in ca["rows"]:
        t2.add_row(r["slug"], r["call"], ", ".join(r["acceptable"]),
                   f"[{'green' if r['ok'] else 'red'}]{r['ok']}[/]")
    console.print(t2)

    if stability_slug:
        console.print(f"[cyan]Stability[/] — re-running {stability_slug} {runs}x (no cache)…")
        st = stability(stability_slug, runs)
        console.print(
            f"  thesis_fit {st['thesis_fit']['values']} range={st['thesis_fit']['range']} "
            f"stdev={st['thesis_fit']['stdev']}"
        )
        console.print(
            f"  weighted   {st['weighted']['values']} range={st['weighted']['range']} "
            f"stdev={st['weighted']['stdev']}"
        )
    console.print("[green]Report ->[/] data/eval_report.json")


def _summary(memos: list[Memo], budget: int | None = None) -> None:
    order = {"Take a meeting": 0, "Watch": 1, "Pass": 2}
    memos = sorted(memos, key=lambda m: (order.get(m.call, 9), -m.weighted_score))
    n_meet = sum(m.call == "Take a meeting" for m in memos)
    title = "VC Triage — pipeline output"
    if budget is not None:
        title += f"  (budget {n_meet}/{budget} meetings of {len(memos)})"
    table = Table(title=title)
    table.add_column("Score", justify="right")
    table.add_column("Call")
    table.add_column("Company")
    table.add_column("slug", style="dim")
    color = {"Take a meeting": "bold green", "Watch": "yellow", "Pass": "dim"}
    for m in memos:
        table.add_row(
            str(m.weighted_score),
            f"[{color.get(m.call,'')}]{m.call}[/]",
            m.name,
            m.slug,
        )
    console.print(table)
    console.print(
        "[dim]Full memo per company -> data/memos/<slug>.md · axis scores + rationale -> "
        "data/analysis.json · print one: [/][cyan]pipeline show <slug>[/]"
    )


@app.command()
def show(slug: str):
    """Print one company's full memo + per-axis scores and rationale to the terminal."""
    analyses = {a.slug: a for a in _load(ANALYSIS_JSON, Analysis)}
    a = analyses.get(slug)
    if a is None:
        console.print(f"[red]No analysis for '{slug}'.[/] Available: {', '.join(sorted(analyses))}")
        raise typer.Exit(1)

    t = Table(title=f"{a.name} — axis scores (weighted {a.weighted_score}/100)")
    t.add_column("Axis"); t.add_column("Score", justify="right"); t.add_column("Weight", justify="right"); t.add_column("Why")
    for k in config.SCORE_WEIGHTS:
        ax = a.axes[k]
        t.add_row(k, str(ax.score), str(config.SCORE_WEIGHTS[k]), ax.rationale)
    console.print(t)
    if a.data_gaps:
        console.print("[yellow]Data gaps:[/] " + "; ".join(a.data_gaps))

    memo_path = config.MEMOS / f"{slug}.md"
    if memo_path.exists():
        from rich.markdown import Markdown

        console.print(Markdown(memo_path.read_text()))
    else:
        console.print(f"[dim]No memo file yet at {memo_path} — run `pipeline memo`.[/]")


if __name__ == "__main__":
    app()
