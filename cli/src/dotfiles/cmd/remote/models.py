"""Domain models for Tailscale-direct Paseo access."""

from pydantic import BaseModel, ConfigDict

PASEO_PORT = 6767


class RemoteStatus(BaseModel):
    """Snapshot of the Mac's phone-access state."""

    model_config = ConfigDict(frozen=True)

    tailscale_connected: bool
    tailnet_ip: str | None
    host: str
    user: str
    paseo_running: bool = False


class ConnectionInfo(BaseModel):
    """How to reach Paseo directly over Tailscale."""

    model_config = ConfigDict(frozen=True)

    host: str
    tailnet_ip: str | None
    paseo_port: int = PASEO_PORT

    @property
    def paseo_addr(self) -> str:
        """The daemon address saved in Paseo desktop and mobile clients."""
        return f"{self.tailnet_ip or self.host}:{self.paseo_port}"
