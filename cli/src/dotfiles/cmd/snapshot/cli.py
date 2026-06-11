"""`dotfiles snapshot` — capture, list, and diff machine-state snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from dotfiles.app.context import AppContext, app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.snapshot.models import Snapshot, SnapshotDiff
from dotfiles.cmd.snapshot.service import (
    capture,
    diff,
    list_snapshots,
    load_snapshot,
    write_snapshot,
)
from dotfiles.console import console, print_status, print_title

snapshot_app = typer.Typer(cls=FuzzyTyperGroup, help="Capture and diff machine-state snapshots.")


def _capture_now(app_ctx: AppContext) -> Snapshot:
    return capture(
        app_ctx.runner,
        dotfiles_dir=app_ctx.dotfiles_dir,
        home=app_ctx.home,
        taken_at=datetime.now(),
    )


def _resolve_token(
    app_ctx: AppContext,
    snaps: list[Path],
    token: str | None,
    default: int,
) -> Snapshot:
    """Resolve a snapshot token ('now', a slug-prefix, or None→use default index)."""
    if token == "now":
        return _capture_now(app_ctx)
    if token is not None:
        match = next((p for p in snaps if p.stem.startswith(token)), None)
        if match is None:
            print_status(console, "error", f"No snapshot matching {token}")
            raise typer.Exit(code=1)
        return load_snapshot(match)
    return load_snapshot(snaps[default])


@snapshot_app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """With no subcommand, capture a snapshot and persist it."""
    if ctx.invoked_subcommand is not None:
        return
    app_ctx = app_context(ctx)
    snap = _capture_now(app_ctx)
    path = write_snapshot(app_ctx.state_dir, snap)
    print_status(
        console,
        "success",
        f"Captured {len(snap.brew.leaves)} leaves, {len(snap.runtimes)} runtimes → {path.name}",
    )


@snapshot_app.command("ls")
def cmd_ls(ctx: typer.Context) -> None:
    """List saved snapshots, newest first."""
    snaps = list_snapshots(app_context(ctx).state_dir)
    print_title(console, "snapshot", "ls")
    if not snaps:
        print_status(console, "info", "No snapshots yet — run `dotfiles snapshot` to capture one")
        return
    for path in snaps:
        console.print(f"  [bold]{path.name}[/]")


def _render_diff(d: SnapshotDiff) -> None:
    if d.is_empty:
        print_status(console, "success", "No drift")
        return
    for name in d.brew_added:
        console.print(f"  [green]+ brew[/] {name}")
    for name in d.brew_removed:
        console.print(f"  [red]- brew[/] {name}")
    for rc in d.runtimes_changed:
        console.print(f"  [yellow]~ {rc.name}[/] {rc.old or '∅'} → {rc.new or '∅'}")
    for sc in d.symlinks_changed:
        marker = "[red]broke[/]" if sc.broke else "[yellow]changed[/]"
        console.print(f"  {marker} {sc.path} → {sc.new_target or '∅'}")
    for agent in d.agent_config_changed:
        console.print(f"  [yellow]~ agent-config[/] {agent}")


@snapshot_app.command("diff")
def cmd_diff(
    ctx: typer.Context,
    a: str | None = typer.Argument(None, help="older snapshot slug-prefix, or 'now'"),
    b: str | None = typer.Argument(None, help="newer snapshot slug-prefix, or 'now'"),
) -> None:
    """Diff two snapshots. No args: previous vs latest. `now`: latest vs a live capture."""
    app_ctx = app_context(ctx)
    snaps = list_snapshots(app_ctx.state_dir)
    print_title(console, "snapshot", "diff")

    if a is None and b is None:
        if len(snaps) < 2:
            print_status(console, "error", "Need at least two snapshots to diff — capture another")
            raise typer.Exit(code=1)
        _render_diff(diff(load_snapshot(snaps[1]), load_snapshot(snaps[0])))
        return

    if a is not None and b is None:
        if not snaps:
            print_status(console, "error", "No snapshots saved yet")
            raise typer.Exit(code=1)
        old = load_snapshot(snaps[0])
        new = _resolve_token(app_ctx, snaps, a, 0)
        _render_diff(diff(old, new))
        return

    _render_diff(diff(_resolve_token(app_ctx, snaps, a, 1), _resolve_token(app_ctx, snaps, b, 0)))
