"""Domain models for the remote (phone-access) entrypoint."""

from pydantic import BaseModel, ConfigDict


class RemoteStatus(BaseModel):
    """Snapshot of the Mac's phone-access state (web clients over Tailscale)."""

    model_config = ConfigDict(frozen=True)

    tailscale_connected: bool
    tailnet_ip: str | None
    host: str
    user: str
    # Full MagicDNS name (host.tailnet.ts.net) when on a tailnet; None otherwise.
    magic_dns: str | None = None
    # The Zellij web client (fallback browser terminal) is serving.
    zellij_web_running: bool = False
    # ygncode pi-web (primary Pi PWA) — present on disk / its service loaded.
    pi_web_installed: bool = False
    pi_web_running: bool = False


class ConnectionInfo(BaseModel):
    """How to reach the phone web clients (over Tailscale)."""

    model_config = ConfigDict(frozen=True)

    host: str
    session: str
    tailnet_ip: str | None
    # Full MagicDNS name (e.g. host.tailnet.ts.net) when the machine is on a
    # tailnet; None off-tailnet. `tailscale serve` issues its TLS cert for this
    # name, so it's what the phone's browser must use.
    magic_dns: str | None = None
    web_port: int = 8082  # Zellij web client (fallback terminal)
    pi_web_port: int = 31415  # ygncode pi-web (primary Pi PWA)

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
    def pi_web_url(self) -> str:
        """The ygncode Pi PWA on the phone — the primary daily surface.

        ygncode self-serves this port over the tailnet; it terminates TLS for
        the MagicDNS name just like the Zellij client.
        """
        return f"https://{self.magic_dns or self.host}:{self.pi_web_port}/"
