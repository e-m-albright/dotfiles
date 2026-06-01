"""Sessions pane: list zellij sessions; Enter attaches (or switches in-zellij)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container
from textual.widgets import Label, ListItem, ListView

from dotfiles.cli.context import AppContext
from dotfiles.core.models import Session
from dotfiles.core.sessions import SessionError, list_sessions
from dotfiles.tui.launcher import in_zellij, zellij_handoff_command

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp


class SessionsPane(Container):
    """Cross-device zellij picker."""

    BORDER_TITLE = "Sessions"
    BINDINGS: ClassVar[list[BindingType]] = [("r", "reload", "Reload")]

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._sessions: list[Session] = []

    @property
    def _app(self) -> MissionControlApp:
        return cast("MissionControlApp", self.app)  # type: ignore[assignment]

    def compose(self) -> ComposeResult:
        yield ListView(id="session-list")

    def on_mount(self) -> None:
        self.action_reload()

    @work(thread=True, exclusive=True)
    def action_reload(self) -> None:
        try:
            sessions = list_sessions(self._ctx.runner)
        except SessionError:
            sessions = []
        self._app.call_from_thread(self._apply_sessions, sessions)

    def _apply_sessions(self, sessions: list[Session]) -> None:
        self._sessions = sessions
        view = self.query_one("#session-list", ListView)
        view.clear()
        for s in sessions:
            tag = "current" if s.current else ("running" if s.running else "exited")
            view.append(ListItem(Label(f"{s.name}  ({tag})"), id=f"sess-{s.name}"))

    def session_names(self) -> list[str]:
        return [s.name for s in self._sessions]

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        name = item_id.removeprefix("sess-")
        if name:
            self._handoff(name)

    def _handoff(self, name: str) -> None:
        command = zellij_handoff_command(name, in_zellij=in_zellij())
        with self._app.suspend():
            os.execvp(command[0], list(command))
