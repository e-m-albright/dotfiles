"""Sessions pane: a touch-first zellij session manager.

Lists sessions (active + resurrectable history), and lets you create, attach,
switch, resurrect, kill, or delete one — each via a deliberate tap so a misfire
on a phone can't yank you somewhere or destroy a session.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

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
    delete_session,
    group_sessions,
    kill_session,
    layout_name_for,
    list_sessions,
    valid_session_name,
)
from dotfiles.tui.launcher import in_zellij, zellij_handoff_command

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp

_NEW_ROW_ID = "new-session"


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


def _section_heading(title: str) -> str:
    """A dim section divider, e.g. 'ACTIVE' or 'RESURRECTABLE'."""
    # Glyph-free on purpose: the row markers (●/◌) carry state, and exotic header
    # glyphs render as tofu in fonts we can't control on the phone.
    return f"[dim]{title}[/]"


def _session_item(s: Session) -> ListItem:
    """A tall, spaced, tappable row for one session (state shown via glyph + accent)."""
    if s.current:
        glyph, state_cls, desc = "●", "is-current", "attached here · tap for options"
    elif s.running:
        glyph, state_cls, desc = "●", "is-running", "running · tap to attach"
    else:
        glyph, state_cls, desc = "◌", "is-exited", "resurrectable · tap to restore"
    label = Label(f"[bold]{glyph}  {s.name}[/]\n   [dim]{desc}[/]")
    return ListItem(label, id=f"sess-{s.name}", classes=f"session-row {state_cls}")


def session_action_buttons(s: Session) -> list[tuple[str, str, str]]:
    """(label, button-id, variant) for the per-session action sheet.

    Button-ids map to actions: ``attach`` (attach/switch/resurrect), ``kill``
    (a live session), ``delete`` (purge an exited one), ``cancel``. The session
    you're attached to offers no destructive action — killing it would tear down
    this very TUI — so it's view-only.
    """
    if s.current:
        return [("Cancel", "cancel", "primary")]
    if s.running:
        return [
            ("Attach", "attach", "success"),
            ("Kill", "kill", "error"),
            ("Cancel", "cancel", "primary"),
        ]
    return [
        ("Restore", "attach", "success"),
        ("Delete", "delete", "error"),
        ("Cancel", "cancel", "primary"),
    ]


class SessionsPane(Container):
    """Cross-device zellij session manager: pick, create, close, resurrect."""

    BORDER_TITLE = "Sessions"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("n", "new_session", "New"),
        Binding("r", "reload", "Reload"),
    ]

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._sessions: list[Session] = []

    @property
    def _app(self) -> MissionControlApp:
        return cast("MissionControlApp", self.app)  # type: ignore[assignment]

    def compose(self) -> ComposeResult:
        yield Static(id="active-agents")
        yield ListView(id="session-list")

    def on_mount(self) -> None:
        self.action_reload()

    @work(thread=True, exclusive=True)
    def action_reload(self) -> None:
        try:
            sessions = list_sessions(self._ctx.runner)
        except SessionError:
            sessions = []
        now = datetime.now()
        agents = live_agents(home=self._ctx.home, now=now)
        clients = attached_client_count(self._ctx.runner) if in_zellij() else None
        self._app.call_from_thread(self._apply_sessions, sessions, agents, now, clients)

    def _apply_sessions(
        self,
        sessions: list[Session],
        agents: list[AgentActivity],
        now: datetime,
        clients: int | None = None,
    ) -> None:
        sections = group_sessions(sessions)
        # Store in display order so session_names()/tests track what's shown.
        self._sessions = [s for _, items in sections for s in items]
        self.query_one("#active-agents", Static).update(_agents_line(agents, now, clients))
        view = self.query_one("#session-list", ListView)
        view.clear()
        # Create is always one tap away, even with zero sessions.
        view.append(ListItem(Label("[b]+  New session[/]"), id=_NEW_ROW_ID, classes="new-row"))
        if not sections:
            view.append(
                ListItem(Label("[dim]no sessions yet[/]"), disabled=True, classes="section-header")
            )
        for title, items in sections:
            view.append(
                ListItem(Label(_section_heading(title)), disabled=True, classes="section-header")
            )
            for s in items:
                view.append(_session_item(s))

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

    def _on_action(self, session: Session, action: str | None) -> None:
        if action == "attach":
            self._handoff(session.name)
        elif action == "kill":
            kill_session(self._ctx.runner, session.name)
            self.notify(f"Killed {session.name}", title="Sessions", severity="warning")
            self.action_reload()
        elif action == "delete":
            delete_session(self._ctx.runner, session.name)
            self.notify(f"Deleted {session.name}", title="Sessions", severity="warning")
            self.action_reload()

    def _on_new_session(self, name: str | None) -> None:
        if not name:
            return
        layout = layout_name_for(self._ctx.home, name)
        command = attach_command(name, exists=False, layout=layout)
        with self._app.suspend():
            os.execvp(command[0], list(command))  # replaces this process; does not return

    def _handoff(self, name: str) -> None:
        command = zellij_handoff_command(name, in_zellij=in_zellij())
        with self._app.suspend():
            os.execvp(command[0], list(command))  # replaces this process; does not return


class _SessionActions(ModalScreen[str | None]):
    """Per-session action sheet: attach/switch, kill, restore, or delete."""

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._s = session

    def compose(self) -> ComposeResult:
        s = self._s
        state = "attached here" if s.current else ("running" if s.running else "resurrectable")
        with Vertical(id="confirm-box"):
            yield Label(f"[b]{s.name}[/]  [dim]· {state}[/]")
            for label, button_id, variant in session_action_buttons(s):
                yield Button(label, variant=variant, id=button_id)  # type: ignore[arg-type]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "cancel" else event.button.id)


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
