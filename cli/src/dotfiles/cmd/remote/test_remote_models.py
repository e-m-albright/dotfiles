from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.result import StepResult


def test_step_result_levels() -> None:
    result = StepResult(level="success", message="ok")
    assert result.level == "success"
    assert result.message == "ok"


def test_connection_info_prefers_tailnet_ip() -> None:
    info = ConnectionInfo(host="mac", tailnet_ip="100.64.0.1")
    assert info.paseo_addr == "100.64.0.1:6767"


def test_connection_info_falls_back_to_host() -> None:
    info = ConnectionInfo(host="mac", tailnet_ip=None)
    assert info.paseo_addr == "mac:6767"


def test_remote_status_defaults_paseo_to_stopped() -> None:
    status = RemoteStatus(
        tailscale_connected=False,
        tailnet_ip=None,
        host="mac",
        user="dev",
    )
    assert status.paseo_running is False
