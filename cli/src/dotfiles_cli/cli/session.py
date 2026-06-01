"""`dotfiles session` / `sesh` commands: list, attach, new, kill zellij sessions."""

import typer

from dotfiles_cli.cli.context import AppContext
from dotfiles_cli.cli.ui import has_errors, render_steps
from dotfiles_cli.console import console
from dotfiles_cli.core.sessions import SessionError, SessionService, attach_command

session_app = typer.Typer(
    help="List/attach/create/kill zellij sessions (same on phone and laptop)."
)


def _ctx(ctx: typer.Context) -> AppContext:
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)
    return app_ctx


@session_app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """With no subcommand, open the fzf picker and attach to the chosen session."""
    if ctx.invoked_subcommand is not None:
        return
    app_ctx = _ctx(ctx)
    try:
        sessions = SessionService(runner=app_ctx.runner).list()
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    if not sessions:
        console.print("No active zellij sessions. Use [bold]sesh new <name>[/] to create one.")
        return
    choice = app_ctx.launcher.pick([s.name for s in sessions])
    if choice:
        app_ctx.launcher.attach(attach_command(choice))


@session_app.command("ls")
def list_sessions(ctx: typer.Context) -> None:
    """List zellij sessions."""
    try:
        sessions = SessionService(runner=_ctx(ctx).runner).list()
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    if not sessions:
        console.print("No active zellij sessions.")
        return
    for s in sessions:
        tag = "current" if s.current else ("running" if s.running else "exited")
        console.print(f"  [bold]{s.name}[/] [dim]({tag})[/]")


@session_app.command()
def attach(ctx: typer.Context, name: str) -> None:
    """Attach to a session (creating it if needed)."""
    _ctx(ctx).launcher.attach(attach_command(name))


@session_app.command()
def new(ctx: typer.Context, name: str) -> None:
    """Create a new session and attach to it."""
    _ctx(ctx).launcher.attach(attach_command(name))


@session_app.command()
def kill(ctx: typer.Context, name: str) -> None:
    """Kill a running session."""
    step = SessionService(runner=_ctx(ctx).runner).kill(name)
    render_steps(console, [step])
    if has_errors([step]):
        raise typer.Exit(code=1)
