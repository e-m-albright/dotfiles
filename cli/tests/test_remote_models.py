from dotfiles.core.models import ConnectionInfo, RemoteStatus, StepResult


def test_step_result_levels() -> None:
    s = StepResult(level="success", message="ok")
    assert s.level == "success"
    assert s.message == "ok"


def test_connection_info_builds_exact_mosh_command() -> None:
    info = ConnectionInfo(
        user="evan",
        host="Evans-MBP-M4",
        session="mobile",
        mosh_server="/opt/homebrew/bin/mosh-server",
        tailnet_ip=None,
    )
    assert info.mosh_command == (
        "mosh --server=/opt/homebrew/bin/mosh-server evan@Evans-MBP-M4 "
        "-- zellij attach --create mobile"
    )
    assert info.startup_command == "zellij attach --create mobile"


def test_remote_status_fields() -> None:
    status = RemoteStatus(
        remote_login_on=True,
        tailscale_connected=False,
        tailnet_ip=None,
        host="Evans-MBP-M4",
        user="evan",
        mosh_server="/opt/homebrew/bin/mosh-server",
    )
    assert status.remote_login_on is True
    assert status.tailscale_connected is False
