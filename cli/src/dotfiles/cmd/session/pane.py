"""Sessions pane: a touch-first zellij session manager.

Lists live sessions and lets you create, attach/switch, or kill one — each via a
deliberate tap so a misfire on a phone can't yank you somewhere or kill the wrong
session. (Detaching is a zellij keybind, `Ctrl o d`, not a list action.)
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from dotfiles.app.context import AppContext
from dotfiles.cmd.session.agent_sessions import live_agents
from dotfiles.cmd.session.models import AgentActivity, Session
from dotfiles.cmd.session.service import (
    SessionError,
    attach_command,
    attached_client_count,
    kill_session,
    layout_name_for,
    list_sessions,
    valid_session_name,
)
from dotfiles.cmd.session.session_info import session_program_titles, zellij_cache_root
from dotfiles.tui.launcher import in_zellij, zellij_handoff_command

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp

_NEW_ROW_ID = "new-session"
_REFRESH_SECONDS = 4.0  # live deck: cheap (one `zellij list-sessions` + a dir scan)


def _agents_line(agents: list[AgentActivity], now: datetime, clients: int | None = None) -> str:
    """One-line summary: attached-client count (when in a session) + live agents."""
    prefix = f"[cyan]👤 {clients} attached[/]  ·  " if clients else ""
    if not agents:
        return prefix + "[dim]No agents active in the last 15m[/]"
    parts: list[str] = []
    for a in agents:
        mins = max(0, int((now - a.last_active).total_seconds() // 60))
        name = Path(a.cwd).name or a.cwd or "?"
        parts.append(f"[green]{a.agent}[/] {name} [dim]{mins}m[/]")
    return prefix + "  ·  ".join(parts)


def live_sessions(sessions: list[Session]) -> list[Session]:
    """Running sessions only, current first then by name (the TUI manages live ones)."""
    return sorted((s for s in sessions if s.running), key=lambda s: (not s.current, s.name))


def _programs_line(programs: Sequence[str], limit: int = 3) -> str:
    """A dim, brand-gold summary of what's running, e.g. ``Claude Code · nvim``.

    Caps the count (with a ``+N`` overflow) and escapes titles so a stray ``[`` in
    a pane title can't be read as console markup.
    """
    shown = [escape(p) for p in programs[:limit]]
    if len(programs) > limit:
        shown.append(f"+{len(programs) - limit}")
    return "   [#cdbf80]" + " · ".join(shown) + "[/]"


def _session_item(s: Session, programs: Sequence[str] = ()) -> ListItem:
    """A tall, spaced, tappable row for one session (state shown via glyph + accent).

    When zellij tells us what's running in the panes, we lead with that preview
    line; the action hint follows, dimmer.
    """
    if s.current:
        state_cls, desc = "is-current", "attached here · tap for options"
    else:
        state_cls, desc = "is-running", "running · tap to attach"
    lines = [f"[bold]●  {s.name}[/]"]
    if programs:
        lines.append(_programs_line(programs))
    lines.append(f"   [dim]{desc}[/]")
    return ListItem(
        Label("\n".join(lines)), id=f"sess-{s.name}", classes=f"session-row {state_cls}"
    )


def session_action_buttons(s: Session) -> list[tuple[str, str, str]]:
    """(label, button-id, variant) for the per-session action sheet.

    Button-ids map to actions: ``attach`` (attach/switch), ``kill``, ``cancel``.
    The session you're attached to offers no destructive action — killing it would
    tear down this very TUI — so it's view-only.
    """
    if s.current:
        return [("[u]C[/u]ancel", "cancel", "primary")]
    return [
        ("[u]A[/u]ttach", "attach", "success"),
        ("[u]K[/u]ill", "kill", "error"),
        ("[u]C[/u]ancel", "cancel", "primary"),
    ]


class SessionsPane(Container):
    """Cross-device zellij session manager: create, attach/switch, kill."""

    BORDER_TITLE = "Sessions"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("n", "new_session", "New"),
        Binding("k", "kill_highlighted", "Kill"),
        Binding("r", "reload", "Reload"),
    ]

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._sessions: list[Session] = []
        # Signatures of the last render, so an unchanged auto-refresh is a no-op
        # (rebuilding the list every tick made it visibly flash).
        self._list_sig: tuple[object, ...] | None = None
        self._agents_sig: str | None = None

    @property
    def _app(self) -> MissionControlApp:
        return cast("MissionControlApp", self.app)  # type: ignore[assignment]

    def compose(self) -> ComposeResult:
        yield Static(id="active-agents")
        yield ListView(id="session-list")

    def on_mount(self) -> None:
        self.action_reload()
        # Keep the deck live so it reflects sessions created/killed elsewhere.
        self.set_interval(_REFRESH_SECONDS, self.action_reload)

    @work(thread=True, exclusive=True)
    def action_reload(self) -> None:
        try:
            sessions = list_sessions(self._ctx.runner)
        except SessionError:
            sessions = []
        now = datetime.now()
        agents = live_agents(home=self._ctx.home, now=now)
        clients = attached_client_count(self._ctx.runner) if in_zellij() else None
        cache_root = zellij_cache_root(self._ctx.home, sys.platform)
        programs = {
            s.name: session_program_titles(cache_root=cache_root, name=s.name)
            for s in sessions
            if s.running
        }
        self._app.call_from_thread(self._apply_sessions, sessions, agents, now, clients, programs)

    async def _apply_sessions(
        self,
        sessions: list[Session],
        agents: list[AgentActivity],
        now: datetime,
        clients: int | None = None,
        programs: dict[str, list[str]] | None = None,
    ) -> None:
        programs = programs or {}
        self._sessions = live_sessions(sessions)

        # Only touch the DOM when the rendered content actually changes — an
        # unchanged auto-refresh tick must not flash the list or the agents line.
        agents_line = _agents_line(agents, now, clients)
        if agents_line != self._agents_sig:
            self.query_one("#active-agents", Static).update(agents_line)
            self._agents_sig = agents_line
        list_sig = tuple(
            (s.name, s.current, s.running, tuple(programs.get(s.name, ()))) for s in self._sessions
        )
        if list_sig == self._list_sig:
            return
        self._list_sig = list_sig

        view = self.query_one("#session-list", ListView)
        # Preserve the cursor across the rebuild so it doesn't jump rows.
        prev = view.highlighted_child
        prev_id = prev.id if prev is not None else None
        # clear() is deferred — await it so the old fixed-id rows are actually
        # gone before we re-append them (otherwise: DuplicateIds on reload).
        await view.clear()
        # Create is always one tap away, even with zero sessions.
        view.append(ListItem(Label("[b]+  New session[/]"), id=_NEW_ROW_ID, classes="new-row"))
        if not self._sessions:
            view.append(ListItem(Label("[dim]no sessions yet[/]"), disabled=True))
        for s in self._sessions:
            view.append(_session_item(s, programs.get(s.name, ())))
        if prev_id is not None:
            restored = next((i for i, it in enumerate(view.children) if it.id == prev_id), None)
            if restored is not None:
                view.index = restored

    def session_names(self) -> list[str]:
        return [s.name for s in self._sessions]

    # ------------------------------------------------------------------ #
    # Interaction
    # ------------------------------------------------------------------ #

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id == _NEW_ROW_ID:
            self.action_new_session()
            return
        if item_id.startswith("sess-"):
            name = item_id.removeprefix("sess-")
            session = next((s for s in self._sessions if s.name == name), None)
            if session is not None:
                self._app.push_screen(
                    _SessionActions(session),
                    lambda action, s=session: self._on_action(s, action),
                )

    def action_new_session(self) -> None:
        self._app.push_screen(_NewSession(), self._on_new_session)

    def action_kill_highlighted(self) -> None:
        """Kill the highlighted session after one confirm (a keyboard shortcut for
        the row's kill action). No-ops on the New row; refuses the current session,
        since killing it would tear down this very TUI."""
        view = self.query_one("#session-list", ListView)
        item = view.highlighted_child
        item_id = item.id if item is not None else None
        if not item_id or not item_id.startswith("sess-"):
            return
        name = item_id.removeprefix("sess-")
        session = next((s for s in self._sessions if s.name == name), None)
        if session is None:
            return
        if session.current:
            self.notify(
                "Can't kill the session you're attached to.",
                title="Sessions",
                severity="warning",
            )
            return
        self._app.push_screen(
            _ConfirmKill(session),
            lambda ok, s=session: self._on_action(s, "kill") if ok else None,
        )

    def _on_action(self, session: Session, action: str | None) -> None:
        if action == "attach":
            self._handoff(session.name)
        elif action == "kill":
            kill_session(self._ctx.runner, session.name)
            self.notify(f"Killed {session.name}", title="Sessions", severity="warning")
            self.action_reload()

    def _on_new_session(self, name: str | None) -> None:
        if not name:
            return
        layout = layout_name_for(self._ctx.home, name)
        command = attach_command(name, exists=False, layout=layout)
        self._app.request_handoff(command)

    def _handoff(self, name: str) -> None:
        command = zellij_handoff_command(name, in_zellij=in_zellij())
        self._app.request_handoff(command)


class _SessionActions(ModalScreen[str | None]):
    """Per-session action sheet: attach/switch or kill. Each option has a hotkey
    (the underlined letter); attach/kill are inert for the current session."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "attach", "Attach"),
        Binding("k", "kill", "Kill"),
        Binding("c", "cancel", "Cancel"),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._s = session

    def compose(self) -> ComposeResult:
        s = self._s
        state = "attached here" if s.current else "running"
        with Vertical(id="confirm-box"):
            yield Label(f"[b]{s.name}[/]  [dim]· {state}[/]")
            for label, button_id, variant in session_action_buttons(s):
                yield Button(label, variant=variant, id=button_id)  # type: ignore[arg-type]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "cancel" else event.button.id)

    def action_attach(self) -> None:
        if not self._s.current:  # attaching to where you already are is a no-op
            self.dismiss("attach")

    def action_kill(self) -> None:
        if not self._s.current:  # killing the current session would tear down the TUI
            self.dismiss("kill")

    def action_cancel(self) -> None:
        self.dismiss(None)


class _ConfirmKill(ModalScreen[bool]):
    """One-tap-to-confirm kill sheet for the `k` shortcut; dismisses True to kill."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("k", "kill", "Kill"),
        Binding("c", "cancel", "Cancel"),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._s = session

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(f"Kill [b]{self._s.name}[/]?")
            yield Button("[u]K[/u]ill", variant="error", id="kill")
            yield Button("[u]C[/u]ancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "kill")

    def action_kill(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class _NewSession(ModalScreen[str | None]):
    """Prompt for a new session name; dismisses with the validated name (or None)."""

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("New session name")
            yield Input(placeholder="e.g. api", id="new-name")
            yield Button("Create", variant="success", id="create")
            yield Button("Cancel", variant="primary", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#new-name", Input).focus()

    def _submit(self) -> None:
        name = self.query_one("#new-name", Input).value.strip()
        self.dismiss(name if valid_session_name(name) else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self._submit()
        else:
            self.dismiss(None)
