from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.result import StepResult


def test_step_result_levels() -> None:
    s = StepResult(level="success", message="ok")
    assert s.level == "success"
    assert s.message == "ok"


def test_connection_info_builds_web_urls() -> None:
    info = ConnectionInfo(host="Evans-MBP-M4", session="mobile", tailnet_ip=None)
    assert info.local_url == "http://127.0.0.1:8082/mobile"
    # Without a known MagicDNS name, the phone URL falls back to the bare host.
    assert info.phone_url == "https://Evans-MBP-M4/mobile"


def test_connection_info_phone_url_prefers_magic_dns() -> None:
    info = ConnectionInfo(
        host="Evans-MBP-M4",
        session="mobile",
        tailnet_ip="100.64.0.1",
        magic_dns="evans-mbp-m4.tailnet.ts.net",
    )
    assert info.phone_url == "https://evans-mbp-m4.tailnet.ts.net/mobile"


def test_connection_info_pi_web_url() -> None:
    info = ConnectionInfo(
        host="mac",
        session="mobile",
        tailnet_ip="100.64.0.1",
        magic_dns="mac.tailnet.ts.net",
    )
    # The primary Pi PWA (ygncode) rides its own port on the same MagicDNS name.
    assert info.pi_web_url == "https://mac.tailnet.ts.net:31415/"


def test_remote_status_fields() -> None:
    status = RemoteStatus(
        tailscale_connected=False,
        tailnet_ip=None,
        host="Evans-MBP-M4",
        user="evan",
    )
    assert status.tailscale_connected is False
    assert status.pi_web_running is False
    assert status.zellij_web_running is False
