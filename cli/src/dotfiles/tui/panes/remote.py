"""Remote pane: render RemoteStatus; toggle/copy/kill actions added in Task 4."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container
from textual.widgets import Static

from dotfiles.cli.context import AppContext
from dotfiles.core.models import RemoteStatus
from dotfiles.core.remote import RemoteService

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp


class RemotePane(Container):
    """Shows the Mac's remote-shell entrypoint state."""

    BORDER_TITLE = "Remote"
    BINDINGS: ClassVar[list[BindingType]] = []

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._status: RemoteStatus | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="remote-body")

    def on_mount(self) -> None:
        self.refresh_status()

    def _service(self) -> RemoteService:
        return RemoteService(
            runner=self._ctx.runner, interactive=self._ctx.interactive, home=self._ctx.home
        )

    @work(thread=True, exclusive=True)
    def refresh_status(self) -> None:
        """Collect status off the UI thread (systemsetup/tailscale can be slow)."""
        status = self._service().status()
        app: MissionControlApp = cast("MissionControlApp", self.app)  # type: ignore[assignment]
        app.call_from_thread(self._apply_status, status)

    def _apply_status(self, status: RemoteStatus) -> None:
        self._status = status
        self.query_one("#remote-body", Static).update(self.render_status_line())

    def render_status_line(self) -> str:
        s = self._status
        if s is None:
            return "collecting…"
        login = "on" if s.remote_login_on else "off"
        tail = s.tailnet_ip or "—"
        tail_state = "connected" if s.tailscale_connected else "down"
        return f"Remote Login: [b]{login}[/]\nTailscale: {tail_state} ({tail})\n{s.user}@{s.host}"
