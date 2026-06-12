"""Render helpers for the cockpit drill-downs (subagents / hooks / permissions)."""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape

from dotfiles.agent import HOOK_INTENTS, VENDORS
from dotfiles.cmd.agent.detail import DenyList, HookWiring, SubagentDetail
from dotfiles.cmd.agent.models import PermissionRow
from dotfiles.cmd.agent.render.overview import GOLD, path_link
from dotfiles.console import console

_VENDOR_COL = {v.name: v.column for v in VENDORS}


def render_subagent_details(details: list[SubagentDetail]) -> None:
    if not details:
        console.print("  [dim](no canonical subagents — ai/subagents is empty)[/]")
        return
    for d in details:
        vendors = "  ".join(
            f"[green]{_VENDOR_COL[v]}[/]" if ok else f"[dim]{_VENDOR_COL[v]}[/]"
            for v, ok in sorted(d.cells.items())
        )
        console.print(f"  [{GOLD}]{escape(d.name):<22}[/] {vendors}")
        if d.description:
            console.print(f"    [dim]{escape(_first_sentence(d.description))}[/]")
    deployed_everywhere = sum(1 for d in details if all(d.cells.values()))
    console.print(
        f"\n  [dim]{len(details)} canonical · {deployed_everywhere} deployed to every "
        "subagent vendor · green = deployed[/]"
    )


def _first_sentence(text: str, limit: int = 96) -> str:
    head = text.split(". ", 1)[0].strip()
    return head if len(head) <= limit else head[: limit - 1] + "…"


def render_hook_wirings(wirings: list[HookWiring], home: Path) -> None:
    intents = [intent for intent, _script in HOOK_INTENTS]
    for w in wirings:
        if w.stance != "deploy":
            console.print(f"  [dim]·[/]  [{GOLD}]{escape(w.vendor):<8}[/] [dim]{escape(w.note)}[/]")
            continue
        if w.note == "extension":
            console.print(
                f"  [green]✓[/]  [{GOLD}]{escape(w.vendor):<8}[/] extension      "
                f"{path_link(w.path, home)}"
            )
            continue
        marks = "  ".join(f"[green]{i}[/]" if i in w.wired else f"[red]{i}[/]" for i in intents)
        glyph = "[green]✓[/]" if len(w.wired) == len(intents) else "[yellow]○[/]"
        console.print(f"  {glyph}  [{GOLD}]{escape(w.vendor):<8}[/] {marks}")
        console.print(
            f"      [dim]{len(w.wired)}/{len(intents)} wired ·[/] {path_link(w.path, home)}"
        )
    console.print(
        "\n  [dim]intents map to ai/agents/shared/hooks/*.sh — green = wired in the "
        "LIVE config · red = missing[/]"
    )


def render_permission_detail(rows: list[PermissionRow], denies: list[DenyList], home: Path) -> None:
    for p in rows:
        qty = (
            f"prefix_rules {p.prefix_rules}"
            if p.prefix_rules
            else f"allow {p.allow}  deny {p.deny}"
        )
        console.print(
            f"  [{GOLD}]{escape(p.label):<26}[/] {qty:<22} {path_link(p.source_path, home)}"
        )
    for deny in denies:
        console.print(
            f"\n[bold]▸ Deny floor[/] [dim]· {escape(deny.label)} · "
            f"{len(deny.entries)} rules — the hard stops, verbatim[/]"
        )
        for entry in deny.entries:
            console.print(f"  [red]✗[/] {escape(entry)}")
