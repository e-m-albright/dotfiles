"""Health/catechism render helpers for `dotfiles agent` commands."""

from __future__ import annotations

import typer
from rich.markup import escape
from rich.table import Table

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.agent import VENDORS
from dotfiles.cmd.agent.models import (
    AgentVerify,
    FileValidation,
    HealthBootstrap,
    Hotspot,
)
from dotfiles.cmd.agent.web_chat import GeminiChunksService
from dotfiles.console import console, print_section, print_title, render_steps
from dotfiles.result import StepResult

_VENDOR_HEADERS = {v.name: v.display_name for v in VENDORS}


def render_validation(v: FileValidation) -> None:
    if v.status == "ok":
        console.print(f"[green]OK  [/] {v.rel_path} [dim]({v.body_lines}-line body)[/]")
    elif v.status == "warn":
        console.print(f"[yellow]WARN[/] {v.rel_path}")
        for w in v.warnings:
            console.print(f"  [yellow]⚠[/] {w}")
    else:
        console.print(f"[red]FAIL[/] {v.rel_path}")
        for e in v.errors:
            console.print(f"  [red]✗[/] {e}")
        for w in v.warnings:
            console.print(f"  [yellow]⚠[/] {w}")


def render_setup_results(agent: str, results: list[StepResult]) -> None:
    """Print step results for one agent under its vendor header."""
    header = _VENDOR_HEADERS.get(agent, agent)
    console.print(f"\n[bold]── {header} ──[/]")
    render_steps(console, results)


def render_vendor(v: AgentVerify) -> None:
    """One agent's verify line: canonical skills vs expected, extras labeled, never alarmed."""
    skills = f"{v.skills_ours}/{v.skills_expected}" if v.skills_expected else "—"
    extras = ""
    if v.skills_external:
        extras += f" [dim]+{v.skills_external} ext[/]"
    if v.skills_foreign:
        extras += f" [dim]+{v.skills_foreign} vendor[/]"
    agents = f"{v.agents_deployed}/{v.agents_expected}" if v.agents_expected else "—"
    console.print(f"[bold]{v.agent}[/]  skills {skills}{extras}  agents {agents}")
    for d in v.drift:
        console.print(f"    [yellow]drift:[/] {d}")
    for probe in v.mcp:
        mark = "[green]✓[/]" if probe.ok else "[red]✗[/]"
        console.print(f"    {mark} mcp:{probe.server} [dim]{probe.detail}[/]")


def verify_capability_probes(runner: ProcessRunner) -> int:
    """Run each cell's probe and check it AGREES with the claimed status — the tether.

    A supported claim (yes/beta/ext) expects the probe to exit 0; a proven-absent
    claim (no) expects it to exit non-zero (the capability really isn't there). A
    mismatch means the matrix has drifted from reality.

    Returns the drift count so the caller can FAIL (non-zero exit) on any drift —
    without that, a scheduled audit or CI step could run this, print red ✗ DRIFT
    lines, and still pass. The probe is only a tether if disagreement has teeth.
    """
    from dotfiles.cmd.agent.capability_matrix import receipts

    print_section(console, "Verify", "probe agrees with claim · ✗ = matrix drifted from reality")
    agree = drift = skipped = 0
    for cap, agent, cell in receipts():
        if not cell.test:
            skipped += 1
            continue
        present = runner.run(("bash", "-lc", cell.test), check=False).exit_code == 0
        expect_present = cell.status in ("yes", "beta", "ext")
        ok = present == expect_present
        agree += ok
        drift += not ok
        mark = "[green]✓ agrees[/]" if ok else "[red]✗ DRIFT[/]"
        verdict = "present" if present else "absent"
        console.print(
            f"  {mark}  [dim]{escape(cap)}·{escape(agent)}[/] "
            f"claim={cell.status} probe={verdict}  [dim]{escape(cell.test[:46])}[/]"
        )
    console.print(f"\n  [dim]{agree} agree · {drift} DRIFT · {skipped} no-probe (source-only)[/]")
    return drift


def render_health(r: HealthBootstrap) -> None:
    print_title(console, "agent", "health")
    console.print(
        f"[bold]Code-health backbone[/]  [dim]scope: {escape(r.scope)} · "
        f"lang: {escape(r.language)}[/]"
    )
    console.print(f"  repo  [dim]{escape(r.target)}[/]")
    console.print(f"  LOC {r.scorecard.loc}   suppressions {r.total_suppressions}")
    if r.created:
        console.print(f"  [green]✓[/] baselines  [dim]{escape(r.baselines_path)}[/]")
    else:
        console.print(
            f"  [yellow]○[/] baselines exist — kept (--force to reseed)  "
            f"[dim]{escape(r.baselines_path)}[/]"
        )
    console.print(f"  [green]✓[/] findings   [dim]{escape(r.findings_path)}[/]")
    render_hotspots(r.scorecard.hotspots)
    console.print()
    console.print(
        "[dim]Next: run [/][bold]/converge[/][dim] to grade (report-<date>.md) "
        "and populate the findings backlog.[/]"
    )


def render_hotspots(rows: tuple[Hotspot, ...]) -> None:
    if not rows:
        return
    console.print()
    console.print("[bold]Hotspots[/] [dim]— churn*LOC; spend refactor effort here first[/]")
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("score", justify="right")
    tbl.add_column("churn", justify="right")
    tbl.add_column("loc", justify="right")
    tbl.add_column("file", style="dim")
    for h in rows[:8]:
        tbl.add_row(str(h.score), str(h.churn), str(h.loc), escape(h.file))
    console.print(tbl)


def gemini_list(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print("[bold]Gemini chunks[/] (target: ~1500 chars each)\n")
    for chunk in chunks:
        console.print(f"  {chunk.char_count:>4} chars  {escape(chunk.name)}")


def gemini_step(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print(
        "[bold]Interactive mode[/]: copy each chunk, paste into Gemini Saved Info,"
        " then press enter."
    )
    console.print("Open https://gemini.google.com/saved-info in another window.\n")
    for chunk in chunks:
        svc.copy(chunk.content)
        console.print(f"[green]Copying {escape(chunk.name)}[/] ({chunk.char_count} chars)")
        typer.prompt(
            "  paste it as a new Saved Info entry, then press enter for next…",
            default="",
            prompt_suffix="",
        )
    console.print(f"\n[green]done[/] — all {len(chunks)} chunks copied.")


def gemini_flycut(svc: GeminiChunksService) -> None:
    chunks = svc.chunks()
    console.print(f"[bold]Loading {len(chunks)} chunks into clipboard history (for Flycut)…[/]")
    for chunk in reversed(chunks):
        svc.copy(chunk.content)
        console.print(f"  [green]✓[/]  {escape(chunk.name)} ({chunk.char_count} chars)")
        svc.wait(0.4)
    console.print(
        "\nNext:\n"
        "  1. Open https://gemini.google.com/saved-info\n"
        "  2. Open Flycut (default shortcut: cmd+shift+V)\n"
        '  3. For each entry in Flycut history (top is chunk 01), click "Add new"\n'
        "     in Gemini, paste, and save.\n"
        "\nIf your Flycut history didn't catch all 7, re-run with --step instead."
    )
