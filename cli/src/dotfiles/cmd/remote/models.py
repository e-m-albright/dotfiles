"""Domain models for the remote (phone-access) entrypoint."""

from pydantic import BaseModel, ConfigDict

# Single home for the two service ports (referenced by service, CLI, and models).
ZELLIJ_WEB_PORT = 8082  # Zellij web client (fallback terminal)
PASEO_PORT = 6767  # Paseo daemon (primary Pi/agent driver)


class RemoteStatus(BaseModel):
    """Snapshot of the Mac's phone-access state."""

    model_config = ConfigDict(frozen=True)

    tailscale_connected: bool
    tailnet_ip: str | None
    host: str
    user: str
    # Full MagicDNS name (host.tailnet.ts.net) when on a tailnet; None otherwise.
    magic_dns: str | None = None
    # The Zellij web client (fallback browser terminal) is serving.
    zellij_web_running: bool = False
    # The Paseo daemon (primary Pi/agent driver) launchd agent is loaded.
    paseo_running: bool = False


class ConnectionInfo(BaseModel):
    """How to reach the phone surfaces (over Tailscale)."""

    model_config = ConfigDict(frozen=True)

    host: str
    session: str
    tailnet_ip: str | None
    # Full MagicDNS name (e.g. host.tailnet.ts.net) when on a tailnet; None
    # off-tailnet. `tailscale serve` issues its TLS cert for this name.
    magic_dns: str | None = None
    web_port: int = ZELLIJ_WEB_PORT
    paseo_port: int = PASEO_PORT

    @property
    def local_url(self) -> str:
        """The Zellij web client on the machine itself, deep-linked to the session."""
        return f"http://127.0.0.1:{self.web_port}/{self.session}"

    @property
    def phone_url(self) -> str:
        """The tailnet URL for the Zellij web client, deep-linked to the session.

        Served over the tailnet by `tailscale serve`, which terminates TLS for
        the machine's MagicDNS name; falls back to the bare host name until the
        tailnet name is known.
        """
        return f"https://{self.magic_dns or self.host}/{self.session}"

    @property
    def paseo_addr(self) -> str:
        """The Paseo daemon address to add in the phone app (direct tailnet connection).

        The Paseo app connects straight to ``<host>:<port>`` over the tailnet with
        the daemon password — no relay, no TLS cert (WireGuard encrypts the hop).
        Prefer the tailnet IP; fall back to the MagicDNS name or bare host.
        """
        return f"{self.tailnet_ip or self.magic_dns or self.host}:{self.paseo_port}"
