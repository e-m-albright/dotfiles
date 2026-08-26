"""Remote pane: render phone-access RemoteStatus; copy the phone web-client URL."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.widgets import Static

from dotfiles.app.context import AppContext
from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.cmd.remote.service import RemoteService

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp


class RemotePane(Container):
    """Shows the Mac's phone-access state (web clients over Tailscale)."""

    BORDER_TITLE = "Remote"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("c", "copy_connect", "Copy Paseo addr"),
        Binding("r", "refresh", "Refresh"),
    ]

    # Tailscale/Paseo state changes out from under a parked phone view; poll
    # gently (each refresh builds a fresh service, so no cached_property reuse).
    _REFRESH_SECONDS = 15.0

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._status: RemoteStatus | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="remote-body")

    def on_mount(self) -> None:
        self.refresh_status()
        self.set_interval(self._REFRESH_SECONDS, self.refresh_status)

    def action_refresh(self) -> None:
        self.refresh_status()

    @property
    def _app(self) -> MissionControlApp:
        return cast("MissionControlApp", self.app)  # type: ignore[assignment]

    def _service(self) -> RemoteService:
        return RemoteService(runner=self._ctx.runner, home=self._ctx.home)

    @work(thread=True, exclusive=True)
    def refresh_status(self) -> None:
        """Collect status off the UI thread (tailscale/launchctl can be slow)."""
        status = self._service().status()
        self._app.call_from_thread(self._apply_status, status)

    def _apply_status(self, status: RemoteStatus) -> None:
        self._status = status
        self.query_one("#remote-body", Static).update(self.render_status_line())

    def render_status_line(self) -> str:
        s = self._status
        if s is None:
            return "collecting…"
        paseo = "running" if s.paseo_running else "stopped"
        web = "running" if s.zellij_web_running else "stopped"
        tail = s.tailnet_ip or "—"
        tail_state = "connected" if s.tailscale_connected else "down"
        return (
            f"Paseo: [b]{paseo}[/]\nZellij web: {web}\n"
            f"Tailscale: {tail_state} ({tail})\n{s.user}@{s.host}"
        )

    def _connection(self) -> ConnectionInfo:
        return self._service().connection_info(self._ctx.settings.default_session)

    def connect_command(self) -> str:
        """The primary phone address (the Paseo daemon)."""
        return self._connection().paseo_addr

    def action_copy_connect(self) -> None:
        self._app.copy_to_clipboard(self.connect_command())
        self.notify("Copied Paseo address", title="Remote")
