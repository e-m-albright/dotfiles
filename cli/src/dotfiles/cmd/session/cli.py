"""`dotfiles session` commands: list, attach, new, kill, prune zellij sessions."""

from collections.abc import Sequence

import typer
from rich.console import Console
from rich.markup import escape

from dotfiles.app.context import AppContext, app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.session import session_name
from dotfiles.cmd.session.models import AgentActivity, Session
from dotfiles.cmd.session.service import (
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAX_COUNT,
    exited_sessions,
    humanize_age,
    live_sessions,
    read_session_inventory,
    sessions_to_prune,
)
from dotfiles.cmd.session.zellij import SessionError, Zellij
from dotfiles.console import console, print_status, print_title, render_and_exit

# Brand-gold, matching the TUI's "what's running" preview line.
_PROGRAM_STYLE = "#cdbf80"


def _zellij(app_ctx: AppContext) -> Zellij:
    """The zellij seam for this host, built from the injected runner and home."""
    return Zellij(app_ctx.runner, home=app_ctx.home)


session_app = typer.Typer(
    cls=FuzzyTyperGroup,
    help="List/attach/create/kill zellij sessions (same on phone and laptop).",
)


@session_app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """With no subcommand, open the fzf picker and attach to the chosen session."""
    if ctx.invoked_subcommand is not None:
        return
    app_ctx = app_context(ctx)
    zellij = _zellij(app_ctx)
    try:
        inventory = read_session_inventory(zellij, app_ctx.runner)
    except SessionError as exc:
        print_status(console, "error", f"zellij error: {exc}")
        raise typer.Exit(code=1) from exc
    if not inventory.sessions:
        print_status(console, "info", "No active zellij sessions — `session new <name>` to create")
        return
    rows = [
        _picker_row(
            session,
            inventory.programs.get(session.name, ()),
            inventory.matched_agents.get(session.name, ()),
        )
        for session in [*live_sessions(inventory.sessions), *exited_sessions(inventory.sessions)]
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


@session_app.command("ls")
def cmd_list_sessions(ctx: typer.Context) -> None:
    """List zellij sessions with what's running and which agents are active."""
    app_ctx = app_context(ctx)
    try:
        inventory = read_session_inventory(_zellij(app_ctx), app_ctx.runner)
    except SessionError as exc:
        print_status(console, "error", f"zellij error: {exc}")
        raise typer.Exit(code=1) from exc
    print_title(console, "session", "ls")
    if not inventory.sessions:
        print_status(console, "info", "No active zellij sessions")
        return
    ordered = [*live_sessions(inventory.sessions), *exited_sessions(inventory.sessions)]
    for session in ordered:
        console.print(
            _ls_line(
                session,
                inventory.programs.get(session.name, ()),
                inventory.matched_agents.get(session.name, ()),
            )
        )


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
        print_status(console, "error", error)
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
        print_status(console, "error", f"zellij error: {exc}")
        raise typer.Exit(code=1) from exc
    names = sessions_to_prune(
        exited_sessions(sessions), max_age_days=max_age_days, max_count=max_count
    )
    if not names:
        print_status(console, "info", "No exited sessions to prune")
        return
    if dry_run:
        print_status(
            console, "warn", f"Would delete {len(names)} exited session(s): {', '.join(names)}"
        )
        return
    render_and_exit(console, zellij.prune(names))
