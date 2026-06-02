"""Domain models for the remote-shell entrypoint."""

from pydantic import BaseModel, ConfigDict


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
        # Route through the dotfiles CLI: attaches the persisted session, or
        # first-creates it with its matching deck layout. A plain command (no
        # quoting/operators) so it survives being pasted into Termius and exec'd
        # directly by mosh-server.
        return f"dotfiles session attach {self.session}"

    @property
    def mosh_command(self) -> str:
        return f"mosh --server={self.mosh_server} {self.user}@{self.host} -- {self.startup_command}"
