"""`dotfiles session` commands: list, attach, new, kill, prune zellij sessions."""

from collections.abc import Sequence
from datetime import datetime

import typer
from rich.console import Console
from rich.markup import escape

from dotfiles.app.context import AppContext, app_context
from dotfiles.cmd.session import session_name
from dotfiles.cmd.session.agent_sessions import live_agents, match_agents_to_sessions
from dotfiles.cmd.session.models import AgentActivity, Session
from dotfiles.cmd.session.service import (
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAX_COUNT,
    exited_sessions,
    humanize_age,
    maybe_prune,
    sessions_to_prune,
)
from dotfiles.cmd.session.zellij import SessionError, Zellij
from dotfiles.console import console, render_and_exit

# Brand-gold, matching the TUI's "what's running" preview line.
_PROGRAM_STYLE = "#cdbf80"


def _zellij(app_ctx: AppContext) -> Zellij:
    """The zellij seam for this host, built from the injected runner and home."""
    return Zellij(app_ctx.runner, home=app_ctx.home)


def _sweep(app_ctx: AppContext) -> None:
    """Run the once-a-day guarded retention sweep when a session list is loaded."""
    maybe_prune(
        _zellij(app_ctx), state_file=app_ctx.state_dir / "session-prune", now=datetime.now()
    )


session_app = typer.Typer(
    help="List/attach/create/kill zellij sessions (same on phone and laptop)."
)


@session_app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """With no subcommand, open the fzf picker and attach to the chosen session."""
    if ctx.invoked_subcommand is not None:
        return
    app_ctx = app_context(ctx)
    zellij = _zellij(app_ctx)
    _sweep(app_ctx)
    try:
        sessions = zellij.list_sessions()
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    if not sessions:
        console.print("No active zellij sessions. Use [bold]session new <name>[/] to create one.")
        return
    rows = [
        _picker_row(s, programs, agents)
        for s, programs, agents in _enriched_rows(app_ctx, sessions)
    ]
    choice = app_ctx.launcher.pick(rows)
    if choice:
        # Picked from the live list, so it already exists.
        layout = zellij.layout_for(choice)
        app_ctx.launcher.attach(zellij.attach_command(choice, exists=True, layout=layout))


def _agent_badge(agents: Sequence[AgentActivity]) -> str:
    """Green badge of agent names active in a session, e.g. ``claude · codex``."""
    return " · ".join(f"[green]{a.agent}[/]" for a in agents)


def _programs_preview(programs: Sequence[str], limit: int = 3) -> str:
    """Brand-gold summary of running pane titles, capped with a ``+N`` overflow.

    Titles are escaped so a stray ``[`` in a pane title can't be read as markup.
    """
    shown = [escape(p) for p in programs[:limit]]
    if len(programs) > limit:
        shown.append(f"+{len(programs) - limit}")
    return f"[{_PROGRAM_STYLE}]" + " · ".join(shown) + "[/]"


def _ls_line(s: Session, programs: Sequence[str] = (), agents: Sequence[AgentActivity] = ()) -> str:
    """One enriched list row: name, state, then active agents + what's running.

    Mirrors the TUI row content (agent badge in green, pane preview in gold) on a
    single line. Exited rows stay minimal — just name and age.
    """
    if not s.running:
        return f"  [bold]{s.name}[/] [dim](exited · {humanize_age(s.created_age_seconds)})[/]"
    tag = "current" if s.current else "running"
    extras = [
        part
        for part in (_agent_badge(agents), _programs_preview(programs) if programs else "")
        if part
    ]
    # Space (not " · ") between the agent badge and the preview: the preview's
    # leading glyph (✳/⠐ from the pane title) already separates them visually.
    detail = "  " + " ".join(extras) if extras else ""
    return f"  [bold]{s.name}[/] [dim]({tag})[/]{detail}"


# Render rich markup to raw ANSI so the same enriched row can be handed to fzf
# (which speaks ANSI via --ansi, not console markup). Truecolor for the gold accent.
_ansi_console = Console(color_system="truecolor", force_terminal=True)


def _ansi(markup: str) -> str:
    """Render a console-markup string to an ANSI-coded line (no trailing newline)."""
    with _ansi_console.capture() as cap:
        _ansi_console.print(markup, end="", soft_wrap=True)
    return cap.get()


def _picker_row(
    s: Session, programs: Sequence[str] = (), agents: Sequence[AgentActivity] = ()
) -> str:
    """A `name<TAB>label` row for the fzf picker: clean key, enriched ANSI label.

    fzf shows/searches the label (the same line `ls` prints) but returns the row
    verbatim, so the caller recovers the session name from the hidden first field.
    """
    return f"{s.name}\t{_ansi(_ls_line(s, programs, agents).strip())}"


def _enriched_rows(
    app_ctx: AppContext, sessions: Sequence[Session]
) -> list[tuple[Session, Sequence[str], Sequence[AgentActivity]]]:
    """Sessions paired with their live enrichment, ordered as the deck shows them.

    Running first (current, then by name), then exited. Each enrichment is
    best-effort — what's running in the panes, and which agents are active in the
    session's cwd subtree — and degrades to empty when zellij's cache is unreadable.
    """
    now = datetime.now()
    zellij = _zellij(app_ctx)
    running = sorted((s for s in sessions if s.running), key=lambda s: (not s.current, s.name))
    programs = {s.name: zellij.program_titles(s.name) for s in running}
    session_cwds = {s.name: cwd for s in running if (cwd := zellij.session_cwd(s.name))}
    matched, _ = match_agents_to_sessions(session_cwds, live_agents(home=app_ctx.home, now=now))
    rows: list[tuple[Session, Sequence[str], Sequence[AgentActivity]]] = [
        (s, programs.get(s.name, ()), matched.get(s.name, [])) for s in running
    ]
    rows.extend((s, (), ()) for s in exited_sessions(sessions))
    return rows


@session_app.command("ls")
def cmd_list_sessions(ctx: typer.Context) -> None:
    """List zellij sessions with what's running and which agents are active."""
    app_ctx = app_context(ctx)
    _sweep(app_ctx)
    try:
        sessions = _zellij(app_ctx).list_sessions()
    except SessionError as exc:
        console.print(f"[red]zellij error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    if not sessions:
        console.print("No active zellij sessions.")
        return
    for s, programs, agents in _enriched_rows(app_ctx, sessions):
        console.print(_ls_line(s, programs, agents))


@session_app.command()
def attach(ctx: typer.Context, name: str) -> None:
    """Attach to a session (creating it, with its deck layout, if needed)."""
    app_ctx = app_context(ctx)
    zellij = _zellij(app_ctx)
    layout = zellij.layout_for(name)
    exists = False
    if layout:  # only the existence check needs a list-sessions round-trip
        try:
            exists = any(s.name == name for s in zellij.list_sessions())
        except SessionError:
            exists = False
    app_ctx.launcher.attach(zellij.attach_command(name, exists=exists, layout=layout))


@session_app.command()
def new(ctx: typer.Context, name: str) -> None:
    """Create a new session and attach to it (with its deck layout if one exists)."""
    app_ctx = app_context(ctx)
    if error := session_name.error(name):
        console.print(f"[red]{error}[/]")
        raise typer.Exit(code=1)
    # `new` always creates: zellij `attach --create` (no layout) or `--session
    # --layout` create the session if absent.
    zellij = _zellij(app_ctx)
    layout = zellij.layout_for(name)
    app_ctx.launcher.attach(zellij.attach_command(name, exists=False, layout=layout))


@session_app.command()
def kill(ctx: typer.Context, name: str) -> None:
    """Kill a running session."""
    step = _zellij(app_context(ctx)).kill_session(name)
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
    zellij = _zellij(app_ctx)
    try:
        sessions = zellij.list_sessions()
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
    render_and_exit(console, zellij.prune(names))
