"""`dotfiles fleet` — live agent sessions across vendors (passive + ledger overlay)."""

import json
from datetime import datetime

import typer

from dotfiles.cli.context import AppContext
from dotfiles.console import console
from dotfiles.core.fleet import list_fleet

fleet_app = typer.Typer(help="Show live agent sessions across Claude/Codex (+ ledger).")

# Vendors not yet passively discovered — surfaced so they aren't silently dropped.
_LEDGER_ONLY = "cursor/pi: ledger-only (no passive discovery yet)"
_BIG_WINDOW = 60 * 24 * 365  # minutes; effectively "all" sessions


def _ctx(ctx: typer.Context) -> AppContext:
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)
    return app_ctx


@fleet_app.callback(invoke_without_command=True)
def show(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="emit JSON"),
    show_all: bool = typer.Option(False, "--all", help="include sessions past the live window"),
) -> None:
    """List live agent sessions, newest first."""
    app_ctx = _ctx(ctx)
    threshold = _BIG_WINDOW if show_all else app_ctx.settings.fleet_live_minutes
    sessions = list_fleet(
        app_ctx.runner,
        home=app_ctx.home,
        state_dir=app_ctx.state_dir,
        now=datetime.now(),
        live_threshold=threshold,
    )
    if as_json:
        console.print_json(json.dumps([s.model_dump(mode="json") for s in sessions]))
        return
    if not sessions:
        console.print("No live agent sessions.")
    for s in sessions:
        where = s.branch or s.cwd
        task = f" · {s.task}" if s.task else ""
        console.print(f"  [bold]{s.vendor}[/] [cyan]{where}[/] [dim]{s.cwd}[/]{task}")
    console.print(f"[dim]{_LEDGER_ONLY}[/]")
