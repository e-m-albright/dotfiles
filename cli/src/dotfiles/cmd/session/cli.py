"""`dotfiles session` commands: list, attach, new, kill, prune zellij sessions."""

from datetime import datetime

import typer

from dotfiles.app.context import AppContext, app_context
from dotfiles.cmd.session.service import (
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAX_COUNT,
    SessionError,
    attach_command,
    exited_sessions,
    humanize_age,
    kill_session,
    layout_name_for,
    list_sessions,
    maybe_prune,
    prune_exited,
    sessions_to_prune,
)
from dotfiles.console import console, render_and_exit


def _sweep(app_ctx: AppContext) -> None:
    """Run the once-a-day guarded retention sweep when a session list is loaded."""
    maybe_prune(app_ctx.runner, state_file=app_ctx.state_dir / "session-prune", now=datetime.now())


session_app = typer.Typer(
    help="List/attach/create/kill zellij sessions (same on phone and laptop)."
)


@session_app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """With no subcommand, open the fzf picker and attach to the chosen session."""
    if ctx.invoked_subcommand is not None:
        return
    app_ctx = app_context(ctx)
    _sweep(app_ctx)
    try:
        sessions = list_sessions(app_ctx.runner)
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    if not sessions:
        console.print("No active zellij sessions. Use [bold]session new <name>[/] to create one.")
        return
    choice = app_ctx.launcher.pick([s.name for s in sessions])
    if choice:
        # Picked from the live list, so it already exists.
        layout = layout_name_for(app_ctx.home, choice)
        app_ctx.launcher.attach(attach_command(choice, exists=True, layout=layout))


@session_app.command("ls")
def cmd_list_sessions(ctx: typer.Context) -> None:
    """List zellij sessions."""
    app_ctx = app_context(ctx)
    _sweep(app_ctx)
    try:
        sessions = list_sessions(app_ctx.runner)
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    if not sessions:
        console.print("No active zellij sessions.")
        return
    for s in sessions:
        if s.current:
            tag = "current"
        elif s.running:
            tag = "running"
        else:
            tag = f"exited · {humanize_age(s.created_age_seconds)}"
        console.print(f"  [bold]{s.name}[/] [dim]({tag})[/]")


@session_app.command()
def attach(ctx: typer.Context, name: str) -> None:
    """Attach to a session (creating it, with its deck layout, if needed)."""
    app_ctx = app_context(ctx)
    layout = layout_name_for(app_ctx.home, name)
    exists = False
    if layout:  # only the existence check needs a list-sessions round-trip
        try:
            exists = any(s.name == name for s in list_sessions(app_ctx.runner))
        except SessionError:
            exists = False
    app_ctx.launcher.attach(attach_command(name, exists=exists, layout=layout))


@session_app.command()
def new(ctx: typer.Context, name: str) -> None:
    """Create a new session and attach to it (with its deck layout if one exists)."""
    app_ctx = app_context(ctx)
    # `new` always creates: zellij `attach --create` (no layout) or `--session
    # --layout` create the session if absent.
    layout = layout_name_for(app_ctx.home, name)
    app_ctx.launcher.attach(attach_command(name, exists=False, layout=layout))


@session_app.command()
def kill(ctx: typer.Context, name: str) -> None:
    """Kill a running session."""
    step = kill_session(app_context(ctx).runner, name)
    render_and_exit(console, [step])


@session_app.command()
def prune(
    ctx: typer.Context,
    max_age_days: int = typer.Option(
        DEFAULT_MAX_AGE_DAYS, "--max-age-days", help="Drop exited sessions older than this."
    ),
    max_count: int = typer.Option(
        DEFAULT_MAX_COUNT, "--max-count", help="Keep at most this many of the newest exited."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be deleted; delete nothing."
    ),
) -> None:
    """Delete old/excess exited sessions (resurrectable ones beyond the retention policy)."""
    app_ctx = app_context(ctx)
    try:
        sessions = list_sessions(app_ctx.runner)
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    names = sessions_to_prune(
        exited_sessions(sessions), max_age_days=max_age_days, max_count=max_count
    )
    if not names:
        console.print("No exited sessions to prune.")
        return
    if dry_run:
        console.print(f"Would delete {len(names)} exited session(s): [bold]{', '.join(names)}[/]")
        return
    render_and_exit(console, prune_exited(app_ctx.runner, names))
