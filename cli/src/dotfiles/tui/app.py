"""Mission Control: the Textual dashboard. Thin adapter over core services."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.widgets import Footer, Header

from dotfiles.cli.context import AppContext, build_real_context
from dotfiles.tui.panes.remote import RemotePane

_STYLES = Path(__file__).parent / "styles" / "dashboard.tcss"


class MissionControlApp(App[None]):
    """Phone-drivable cockpit over the dotfiles core services."""

    CSS_PATH = _STYLES
    TITLE = "Mission Control"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, *, ctx: AppContext | None = None) -> None:
        super().__init__()
        self._ctx = ctx if ctx is not None else build_real_context(interactive=True)

    @property
    def ctx(self) -> AppContext:
        return self._ctx

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield RemotePane(self._ctx)
        yield Footer()
