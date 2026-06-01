"""Remote pane: render RemoteStatus; toggle/copy/kill actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from dotfiles.cli.context import AppContext
from dotfiles.core.models import ConnectionInfo, RemoteStatus, StepResult
from dotfiles.core.remote import RemoteService

if TYPE_CHECKING:
    from dotfiles.tui.app import MissionControlApp


class RemotePane(Container):
    """Shows the Mac's remote-shell entrypoint state."""

    BORDER_TITLE = "Remote"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("t", "toggle_login", "Toggle Remote Login"),
        Binding("c", "copy_connect", "Copy connect cmd"),
        Binding("k", "kill_sessions", "Kill mosh sessions"),
    ]

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._status: RemoteStatus | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="remote-body")

    def on_mount(self) -> None:
        self.refresh_status()

    @property
    def _app(self) -> MissionControlApp:
        return cast("MissionControlApp", self.app)  # type: ignore[assignment]

    def _service(self) -> RemoteService:
        return RemoteService(
            runner=self._ctx.runner, interactive=self._ctx.interactive, home=self._ctx.home
        )

    @work(thread=True, exclusive=True)
    def refresh_status(self) -> None:
        """Collect status off the UI thread (systemsetup/tailscale can be slow)."""
        status = self._service().status()
        self._app.call_from_thread(self._apply_status, status)

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

    def _connection(self) -> ConnectionInfo:
        return self._service().connection_info(self._ctx.settings.default_session)

    def connect_command(self) -> str:
        return self._connection().mosh_command

    def action_copy_connect(self) -> None:
        cmd = self.connect_command()
        self._app.copy_to_clipboard(cmd)
        self.notify("Copied connect command", title="Remote")

    def toggle_login_plan(self) -> StepResult:
        """Plan the toggle. Over a non-interactive session sudo will fail — warn instead."""
        if not self._ctx.interactive:
            return StepResult(
                level="warn",
                message="Toggling Remote Login needs sudo on the host (run on the Mac directly).",
            )
        return StepResult(
            level="info", message="Run `dotfiles remote setup` to enable on the host."
        )

    def action_toggle_login(self) -> None:
        result = self.toggle_login_plan()
        severity = "warning" if result.level == "warn" else "information"
        self.notify(result.message, severity=severity)  # type: ignore[arg-type]

    def action_kill_sessions(self) -> None:
        """Self-disconnect guard: killing mosh-server ends THIS session — confirm first."""
        self._app.push_screen(_ConfirmKill(), self._on_kill_confirmed)

    def _on_kill_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        self._service().disable(dry_run=False, kill_sessions=True)
        self.notify("Killed mosh sessions", title="Remote", severity="warning")
        self.refresh_status()


class _ConfirmKill(ModalScreen[bool]):
    """Confirm before killing mosh-server (which disconnects this very session)."""

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("Killing mosh sessions disconnects YOU. Continue?")
            yield Button("Kill", variant="error", id="kill")
            yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "kill")
