"""`dotfiles ledger` — log / list / prune agent-activity records."""

from datetime import datetime, timedelta

import typer

from dotfiles.cli.context import AppContext
from dotfiles.console import console
from dotfiles.core.ledger import append, prune, read
from dotfiles.core.models import LedgerEntry

ledger_app = typer.Typer(help="Append-only ledger of what each agent session is doing.")


def _ctx(ctx: typer.Context) -> AppContext:
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)
    return app_ctx


@ledger_app.command("log")
def cmd_log(
    ctx: typer.Context,
    session: str = typer.Option(..., "--session"),
    vendor: str = typer.Option(..., "--vendor"),
    cwd: str = typer.Option(..., "--cwd"),
    status: str = typer.Option(..., "--status"),
    branch: str = typer.Option(None, "--branch"),
    task: str = typer.Option(None, "--task"),
) -> None:
    """Append one activity record (also callable by the hot-path hook)."""
    append(
        _ctx(ctx).state_dir,
        LedgerEntry(
            ts=datetime.now(),
            session_id=session,
            vendor=vendor,
            cwd=cwd,
            branch=branch,
            task=task,
            status=status,
        ),
    )


@ledger_app.command("ls")
def cmd_ls(ctx: typer.Context) -> None:
    """List recent ledger entries."""
    entries = read(_ctx(ctx).state_dir)
    if not entries:
        console.print("Ledger is empty.")
        return
    for e in entries:
        task = e.task or "—"
        console.print(f"  [bold]{e.vendor}[/] {e.session_id} [dim]{e.cwd}[/] · {task} ({e.status})")


@ledger_app.command("prune")
def cmd_prune(
    ctx: typer.Context,
    older_than: int = typer.Option(7, "--older-than", help="days"),
) -> None:
    """Drop ledger entries older than N days."""
    cutoff = datetime.now() - timedelta(days=older_than)
    removed = prune(_ctx(ctx).state_dir, older_than=cutoff)
    console.print(f"Pruned [bold]{removed}[/] entries older than {older_than}d.")
