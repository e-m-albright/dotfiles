from io import StringIO

from rich.console import Console

from dotfiles_cli.cli.ui import render_steps
from dotfiles_cli.core.models import StepResult


def test_render_steps_writes_each_message_with_a_glyph() -> None:
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=100)
    render_steps(
        console,
        [
            StepResult(level="success", message="ready"),
            StepResult(level="warn", message="careful"),
            StepResult(level="error", message="boom"),
            StepResult(level="info", message="noted"),
        ],
    )
    out = buf.getvalue()
    assert "ready" in out
    assert "careful" in out
    assert "boom" in out
    assert "noted" in out
    # success/warn/error/info use distinct leading glyphs
    assert "✓" in out
    assert "⚠" in out
    assert "✗" in out
    assert "•" in out


def test_has_errors() -> None:
    from dotfiles_cli.cli.ui import has_errors

    assert has_errors([StepResult(level="error", message="x")]) is True
    assert has_errors([StepResult(level="warn", message="x")]) is False
    assert has_errors([]) is False


def test_render_connection_info_warns_when_no_tailscale() -> None:
    from io import StringIO

    from dotfiles_cli.cli.ui import render_connection_info
    from dotfiles_cli.core.models import ConnectionInfo

    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=200)
    info = ConnectionInfo(
        user="evan",
        host="Evans-MBP-M4",
        session="mobile",
        mosh_server="/opt/homebrew/bin/mosh-server",
        tailnet_ip=None,
    )
    render_connection_info(console, info)
    out = buf.getvalue()
    assert "Tailscale does not look connected" in out
    assert "evan" in out
    assert "mosh --server=" in out


def test_render_connection_info_offers_picker_command() -> None:
    from io import StringIO

    from dotfiles_cli.cli.ui import render_connection_info
    from dotfiles_cli.core.models import ConnectionInfo

    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=200)
    info = ConnectionInfo(
        user="evan",
        host="mac",
        session="mobile",
        mosh_server="/opt/homebrew/bin/mosh-server",
        tailnet_ip="100.64.0.1",
    )
    render_connection_info(console, info)
    out = buf.getvalue()
    # direct-attach command AND a picker variant are both offered
    assert "zellij attach --create mobile" in out
    assert "dotfiles sesh" in out
