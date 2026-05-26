"""Typer CLI for yt-ingest."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .bookmarks import extract_youtube_urls, write_tsv
from .pipeline import (
    append_failures,
    append_results,
    process_batch,
    read_results,
    retry_failures,
    write_results,
)
from .transcript import DEFAULT_TRANSCRIPT_MODEL, process_transcript_batch
from .triage import classify, write_keep_skip_tsvs
from .writer import write_all

app = typer.Typer(
    help="YouTube bookmarks -> Learn/ queue ingestion with Gemini + oEmbed verification.",
    no_args_is_help=True,
)
console = Console()


def _read_tsv(path: Path) -> list[dict]:
    lines = path.read_text().strip().split("\n")
    headers = lines[0].split("\t")
    return [dict(zip(headers, line.split("\t"))) for line in lines[1:] if line.strip()]


# ---------- parse ----------


@app.command()
def parse(
    bookmarks_html: Annotated[
        Path, typer.Argument(help="Netscape bookmarks HTML export")
    ],
    out_tsv: Annotated[Path, typer.Argument(help="Output TSV (folder, title, url)")],
) -> None:
    """Extract YouTube URLs from a bookmarks HTML file."""
    rows = extract_youtube_urls(bookmarks_html)
    write_tsv(rows, out_tsv)
    console.print(
        f"[green]Extracted {len(rows)} unique YouTube URLs -> {out_tsv}[/green]"
    )


# ---------- triage ----------


@app.command()
def triage(
    in_tsv: Annotated[Path, typer.Argument(help="Parsed URLs TSV")],
    keep_tsv: Annotated[
        Path, typer.Option("--keep", help="Output: keepers TSV")
    ] = Path("yt_keep.tsv"),
    skip_tsv: Annotated[Path, typer.Option("--skip", help="Output: skips TSV")] = Path(
        "yt_skip.tsv"
    ),
) -> None:
    """Classify URLs into keep / skip using default low-signal patterns."""
    rows = _read_tsv(in_tsv)
    keep, skip = classify(rows)
    write_keep_skip_tsvs(keep, skip, keep_tsv, skip_tsv)
    console.print(f"[green]Keep: {len(keep)} -> {keep_tsv}[/green]")
    console.print(f"[yellow]Skip: {len(skip)} -> {skip_tsv}[/yellow]")


# ---------- process ----------


@app.command()
def process(
    keep_tsv: Annotated[Path, typer.Argument(help="Keepers TSV")],
    results_tsv: Annotated[Path, typer.Argument(help="Results TSV (appended)")],
    start: Annotated[int, typer.Option(help="Start row index")] = 0,
    end: Annotated[
        int, typer.Option(help="End row index (exclusive); -1 for all")
    ] = -1,
    parallelism: Annotated[
        int, typer.Option(help="Concurrent Gemini calls (>10 hits rate limits)")
    ] = 10,
) -> None:
    """Run Gemini + oEmbed for a row range from the keepers TSV. Appends to results TSV."""
    rows = _read_tsv(keep_tsv)
    sliced = rows[start:end] if end >= 0 else rows[start:]
    console.print(f"[cyan]Processing {len(sliced)} rows ({start}:{end})...[/cyan]")
    tuples = [(r["folder"], r["title"], r["url"]) for r in sliced]
    results = process_batch(tuples, parallelism=parallelism)
    for r in results:
        status = "[green]OK[/green]" if r["verified"] else "[yellow]??[/yellow]"
        console.print(f"  {status} {r['oembed_title'][:60]!r} -- {r['note']}")
    append_results(results, results_tsv)
    console.print(f"[green]Wrote {len(results)} rows -> {results_tsv}[/green]")


# ---------- process-transcript ----------


@app.command("process-transcript")
def process_transcript_cmd(
    keep_tsv: Annotated[Path, typer.Argument(help="Keepers TSV")],
    results_tsv: Annotated[Path, typer.Argument(help="Results TSV (appended)")],
    start: Annotated[int, typer.Option(help="Start row index")] = 0,
    end: Annotated[
        int, typer.Option(help="End row index (exclusive); -1 for all")
    ] = -1,
    parallelism: Annotated[
        int, typer.Option(help="Concurrent yt-dlp + summarize calls")
    ] = 5,
    model: Annotated[
        str,
        typer.Option(
            help="Gemini model for summarization (text-only, default Flash Lite for separate quota)"
        ),
    ] = DEFAULT_TRANSCRIPT_MODEL,
) -> None:
    """Fetch transcripts via yt-dlp and summarize via Gemini text model.

    Use this when Gemini Pro's video-watching quota is exhausted or when you
    want grounded summaries (model reads actual transcript, not hallucinated content).
    """
    rows = _read_tsv(keep_tsv)
    sliced = rows[start:end] if end >= 0 else rows[start:]
    console.print(
        f"[cyan]Transcript-mode processing {len(sliced)} rows (model={model})...[/cyan]"
    )
    tuples = [(r["folder"], r["title"], r["url"]) for r in sliced]
    results = process_transcript_batch(tuples, parallelism=parallelism, model=model)
    for r in results:
        status = "[green]OK[/green]" if r["verified"] else "[yellow]??[/yellow]"
        console.print(f"  {status} {r['oembed_title'][:60]!r} -- {r['note']}")
    append_results(results, results_tsv)
    verified = sum(1 for r in results if r["verified"])
    console.print(
        f"[green]Wrote {len(results)} rows ({verified} verified) -> {results_tsv}[/green]"
    )


# ---------- retry ----------


@app.command()
def retry(
    results_tsv: Annotated[
        Path, typer.Argument(help="Results TSV (will be updated in place)")
    ],
    failures_md: Annotated[
        Path, typer.Argument(help="Markdown checklist for persistent failures")
    ],
    parallelism: Annotated[int, typer.Option(help="Concurrent retries")] = 8,
) -> None:
    """Retry every unverified row once. Update TSV; append persistent failures to markdown."""
    rows = read_results(results_tsv)
    recovered, still_failed = retry_failures(rows, parallelism=parallelism)

    by_url = {r["url"]: r for r in rows}
    for r in recovered + still_failed:
        by_url[r["url"]] = r
    write_results(list(by_url.values()), results_tsv)

    new_failures_count = append_failures(still_failed, failures_md)
    console.print(f"[green]Recovered: {len(recovered)}[/green]")
    console.print(
        f"[yellow]Still failed: {len(still_failed)} (+{new_failures_count} new appended to {failures_md})[/yellow]"
    )


# ---------- write ----------


@app.command()
def write(
    results_tsv: Annotated[Path, typer.Argument(help="Results TSV")],
    queue_dir: Annotated[
        Path, typer.Argument(help="Output directory for Watch-*.md files")
    ],
    force: Annotated[bool, typer.Option(help="Overwrite existing files")] = False,
) -> None:
    """Generate Learn/ queue items from a results TSV."""
    written, skipped = write_all(results_tsv, queue_dir, force=force)
    console.print(f"[green]Wrote {len(written)} items to {queue_dir}[/green]")
    if skipped:
        console.print(f"[yellow]Skipped {len(skipped)}: dupes/existing[/yellow]")


# ---------- full pipeline ----------


@app.command()
def run(
    bookmarks_html: Annotated[
        Path, typer.Argument(help="Netscape bookmarks HTML export")
    ],
    queue_dir: Annotated[
        Path, typer.Option("--queue-dir", help="Output dir for queue items")
    ] = Path("./Learn/Professional"),
    failures_md: Annotated[
        Path, typer.Option("--failures", help="Failures markdown checklist")
    ] = Path("./youtube-failures.md"),
    workdir: Annotated[Path, typer.Option(help="Workdir for intermediate TSVs")] = Path(
        "/tmp/yt-ingest"
    ),
    batch_size: Annotated[int, typer.Option(help="Rows per processing batch")] = 20,
    parallelism: Annotated[
        int, typer.Option(help="Concurrent Gemini calls per batch")
    ] = 10,
    force: Annotated[bool, typer.Option(help="Overwrite existing queue items")] = False,
) -> None:
    """Full pipeline: parse -> triage -> process (in batches) -> retry -> write."""
    workdir.mkdir(parents=True, exist_ok=True)
    all_urls = workdir / "all.tsv"
    keep_tsv = workdir / "keep.tsv"
    skip_tsv = workdir / "skip.tsv"
    results_tsv = workdir / "results.tsv"
    results_tsv.unlink(missing_ok=True)

    # 1. Parse
    rows = extract_youtube_urls(bookmarks_html)
    write_tsv(rows, all_urls)
    console.print(f"[cyan]Parsed {len(rows)} unique YouTube URLs.[/cyan]")

    # 2. Triage
    keep, skip = classify(rows)
    write_keep_skip_tsvs(keep, skip, keep_tsv, skip_tsv)
    console.print(f"[cyan]Triage: {len(keep)} keep, {len(skip)} skip.[/cyan]")

    # 3. Process in batches
    keep_tuples = [(r["folder"], r["title"], r["url"]) for r in keep]
    for i in range(0, len(keep_tuples), batch_size):
        batch = keep_tuples[i : i + batch_size]
        console.print(
            f"[cyan]Batch {i // batch_size + 1}: rows {i}-{i + len(batch)}[/cyan]"
        )
        results = process_batch(batch, parallelism=parallelism)
        for r in results:
            status = "[green]OK[/green]" if r["verified"] else "[yellow]??[/yellow]"
            console.print(f"  {status} {r['oembed_title'][:60]!r} -- {r['note']}")
        append_results(results, results_tsv)

    # 4. Retry
    console.print("[cyan]Retrying failures...[/cyan]")
    all_results = read_results(results_tsv)
    recovered, still_failed = retry_failures(all_results)
    by_url = {r["url"]: r for r in all_results}
    for r in recovered + still_failed:
        by_url[r["url"]] = r
    write_results(list(by_url.values()), results_tsv)
    new_failures = append_failures(still_failed, failures_md)
    console.print(f"[green]Recovered {len(recovered)} on retry.[/green]")
    console.print(
        f"[yellow]{len(still_failed)} still failed (+{new_failures} appended to {failures_md}).[/yellow]"
    )

    # 5. Write queue items
    written, skipped = write_all(results_tsv, queue_dir, force=force)
    console.print(
        f"\n[bold green]Done. Wrote {len(written)} queue items to {queue_dir}.[/bold green]"
    )
    if skipped:
        console.print(f"[yellow]Skipped {len(skipped)} dupes/existing.[/yellow]")
