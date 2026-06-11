"""Render the harness manifest for `dotfiles agent instructions`."""

from __future__ import annotations

from rich.markup import escape
from rich.table import Table

from dotfiles.cmd.agent.instructions import ContextItem, InstructionsManifest, LoadMode
from dotfiles.cmd.agent.render.overview import GOLD
from dotfiles.console import console


def _fmt_tokens(tokens: int) -> str:
    """A compact token gauge: ~12.3k / ~840."""
    if tokens >= 1000:
        return f"~{tokens / 1000:.1f}k"
    return f"~{tokens}"


def _section(title: str, hint: str) -> None:
    console.print(f"\n[bold]▸ {escape(title)}[/]  [dim]{escape(hint)}[/]")


def _context_table(items: list[ContextItem]) -> None:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("source")
    table.add_column("tokens", justify="right", style="dim")
    table.add_column("files", justify="right", style="dim")
    table.add_column("note", style="dim", max_width=52)
    for item in items:
        files = str(item.count) if item.count else "—"
        table.add_row(
            f"[{GOLD}]{escape(item.name)}[/]",
            _fmt_tokens(item.est_tokens),
            files,
            escape(item.note),
        )
    console.print(table)


def _harness_table(items: list[ContextItem]) -> None:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("source")
    table.add_column("count", justify="right", style="dim")
    table.add_column("note", style="dim", max_width=60)
    for item in items:
        table.add_row(f"[{GOLD}]{escape(item.name)}[/]", str(item.count), escape(item.note))
    console.print(table)


def _render_map(manifest: InstructionsManifest) -> None:
    _section(
        "The engineering map", "doctrine → enforcement → layers → tools · full: ENGINEERING.md"
    )
    width = max((len(c.name) for c in manifest.columns), default=8)
    for col in manifest.columns:
        console.print(
            f"  [{GOLD}]{escape(col.name):<{width}}[/]  {escape(col.ids)}\n"
            f"  {' ' * width}  [dim]{escape(col.source)}[/]"
        )


def render_instructions(manifest: InstructionsManifest) -> None:
    """Print the full harness manifest: the map, then context by load mode."""
    _render_map(manifest)

    default_tok = manifest.tokens_for(LoadMode.default)
    _section("Loaded by default", f"{_fmt_tokens(default_tok)} tok in context every session")
    _context_table(manifest.items_for(LoadMode.default))

    _section("Reachable on demand", "0 cost until pulled — trigger, link, or dispatch")
    _context_table(manifest.items_for(LoadMode.reachable))

    _section("Active harness", "shapes behavior, not context text")
    _harness_table(manifest.items_for(LoadMode.harness))

    console.print(
        f"\n[dim]Budget paid every session: [/][bold]{_fmt_tokens(default_tok)} tok[/]"
        f"[dim] · reachable corpus: {_fmt_tokens(manifest.tokens_for(LoadMode.reachable))} tok[/]"
    )


def manifest_json(manifest: InstructionsManifest) -> dict[str, object]:
    """Structured manifest for `--json`, with the per-mode token totals folded in."""
    return {
        "items": [item.model_dump(mode="json") for item in manifest.items],
        "columns": [col.model_dump(mode="json") for col in manifest.columns],
        "totals": {
            "default_tokens": manifest.tokens_for(LoadMode.default),
            "reachable_tokens": manifest.tokens_for(LoadMode.reachable),
        },
    }
