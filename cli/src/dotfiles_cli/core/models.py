"""Domain models. All immutable pydantic models, returned by the core layer."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CommandResult(BaseModel):
    """Result of running an external command via a ProcessRunner port."""

    model_config = ConfigDict(frozen=True)

    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


StepLevel = Literal["success", "info", "warn", "error"]


class StepResult(BaseModel):
    """One reported step of a remote action, rendered by the CLI/TUI."""

    model_config = ConfigDict(frozen=True)

    level: StepLevel
    message: str


class RemoteStatus(BaseModel):
    """Snapshot of the Mac's remote-shell entrypoint state."""

    model_config = ConfigDict(frozen=True)

    remote_login_on: bool
    tailscale_connected: bool
    tailnet_ip: str | None
    host: str
    user: str
    mosh_server: str


class ConnectionInfo(BaseModel):
    """Everything needed to connect from Termius."""

    model_config = ConfigDict(frozen=True)

    user: str
    host: str
    session: str
    mosh_server: str
    tailnet_ip: str | None

    @property
    def startup_command(self) -> str:
        return f"zellij attach --create {self.session}"

    @property
    def mosh_command(self) -> str:
        return f"mosh --server={self.mosh_server} {self.user}@{self.host} -- {self.startup_command}"
