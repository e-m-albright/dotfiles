from io import StringIO

from rich.console import Console

from dotfiles.console import render_steps
from dotfiles.result import StepResult


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


def test_render_steps_escapes_rich_markup_in_message() -> None:
    """Brackets in step messages (e.g. [HTTP 403]) must not be treated as markup."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=100)
    render_steps(console, [StepResult(level="error", message="oops [HTTP 403]")])
    out = buf.getvalue()
    assert "[HTTP 403]" in out


def test_has_errors() -> None:
    from dotfiles.console import has_errors

    assert has_errors([StepResult(level="error", message="x")]) is True
    assert has_errors([StepResult(level="warn", message="x")]) is False
    assert has_errors([]) is False


def test_render_connection_info_warns_when_no_tailscale() -> None:
    from io import StringIO

    from dotfiles.cmd.remote.cli import render_connection_info
    from dotfiles.cmd.remote.models import ConnectionInfo

    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=200)
    info = ConnectionInfo(host="Evans-MBP-M4", session="mobile", tailnet_ip=None)
    render_connection_info(console, info)
    out = buf.getvalue()
    assert "Tailscale not connected" in out
    assert "http://127.0.0.1:8082/mobile" in out


def test_render_connection_info_shows_web_client_urls() -> None:
    from io import StringIO

    from dotfiles.cmd.remote.cli import render_connection_info
    from dotfiles.cmd.remote.models import ConnectionInfo

    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=200)
    info = ConnectionInfo(
        host="mac",
        session="mobile",
        tailnet_ip="100.64.0.1",
        magic_dns="mac.tailnet.ts.net",
    )
    render_connection_info(console, info)
    out = buf.getvalue()
    # Primary: the Paseo daemon address. Fallback: the Zellij web URLs + token hint.
    assert "100.64.0.1:6767" in out
    assert "http://127.0.0.1:8082/mobile" in out
    assert "https://mac.tailnet.ts.net/mobile" in out
    assert "dfs remote web --new-token" in out
