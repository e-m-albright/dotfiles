from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.result import StepResult


def test_step_result_levels() -> None:
    s = StepResult(level="success", message="ok")
    assert s.level == "success"
    assert s.message == "ok"


def test_connection_info_builds_web_urls() -> None:
    info = ConnectionInfo(host="test-mac-m4", session="mobile", tailnet_ip=None)
    assert info.local_url == "http://127.0.0.1:8082/mobile"
    # Without a known MagicDNS name, the phone URL falls back to the bare host.
    assert info.phone_url == "https://test-mac-m4/mobile"


def test_connection_info_phone_url_prefers_magic_dns() -> None:
    info = ConnectionInfo(
        host="test-mac-m4",
        session="mobile",
        tailnet_ip="100.64.0.1",
        magic_dns="evans-mbp-m4.tailnet.ts.net",
    )
    assert info.phone_url == "https://evans-mbp-m4.tailnet.ts.net/mobile"


def test_connection_info_paseo_addr_prefers_tailnet_ip() -> None:
    info = ConnectionInfo(
        host="mac",
        session="mobile",
        tailnet_ip="100.64.0.1",
        magic_dns="mac.tailnet.ts.net",
    )
    # The Paseo app connects to the tailnet IP:port directly (no relay/TLS).
    assert info.paseo_addr == "100.64.0.1:6767"


def test_connection_info_paseo_addr_falls_back_to_host() -> None:
    info = ConnectionInfo(host="mac", session="mobile", tailnet_ip=None)
    assert info.paseo_addr == "mac:6767"


def test_remote_status_fields() -> None:
    status = RemoteStatus(
        tailscale_connected=False,
        tailnet_ip=None,
        host="test-mac-m4",
        user="evan",
    )
    assert status.tailscale_connected is False
    assert status.paseo_running is False
    assert status.zellij_web_running is False
