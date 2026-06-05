"""Mission Control: the Textual dashboard. Thin adapter over core services."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.widgets import Footer, Static

from dotfiles.app.context import AppContext, build_real_context
from dotfiles.banner import COMPACT_LINES, gradient_banner
from dotfiles.cmd.remote.pane import RemotePane
from dotfiles.cmd.session.pane import SessionsPane

_STYLES = Path(__file__).parent / "styles" / "dashboard.tcss"


class MissionControlApp(App[None]):
    """Phone-drivable cockpit over the dotfiles core services."""

    CSS_PATH = _STYLES
    TITLE = "Mission Control"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, *, ctx: AppContext | None = None) -> None:
        super().__init__()
        self._ctx = ctx if ctx is not None else build_real_context(interactive=sys.stdin.isatty())
        # Command to exec *after* the app exits — set when handing the terminal
        # off to zellij. We exit cleanly first so Textual fully restores the
        # terminal (blocking stdin, cooked mode, mouse off) before the exec;
        # exec'ing from inside a running/suspended app leaves stdin in a state
        # that swallows the new process's keystrokes.
        self.handoff_command: tuple[str, ...] | None = None

    @property
    def ctx(self) -> AppContext:
        return self._ctx

    def request_handoff(self, command: Sequence[str]) -> None:
        """Quit the TUI and hand the terminal to `command` once `run()` returns."""
        self.handoff_command = tuple(command)
        self.exit()

    def on_mount(self) -> None:
        self.sub_title = "▚▚ phone command deck ▚▚"

    def compose(self) -> ComposeResult:
        yield Static(gradient_banner(COMPACT_LINES), id="banner")
        with Vertical(id="panes"):
            yield RemotePane(self._ctx)
            yield SessionsPane(self._ctx)
        yield Footer()
