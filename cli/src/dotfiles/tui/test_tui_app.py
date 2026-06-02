"""Mission Control TUI app boots and mounts panes."""

import pytest
from typer.testing import CliRunner

from dotfiles.app.main import app as cli_app
from dotfiles.testing.fakes import make_fake_context
from dotfiles.tui.app import MissionControlApp

runner = CliRunner()


@pytest.mark.asyncio
async def test_app_boots_with_injected_context():
    app = MissionControlApp(ctx=make_fake_context())
    async with app.run_test() as pilot:
        await pilot.pause()
        # Title bar renders the brand; app is running.
        assert "MISSION CONTROL" in app.title.upper()
        assert app.is_running


def test_help_still_works_and_lists_tui():
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "tui" in result.stdout


def test_tui_command_is_registered(monkeypatch):
    launched: list[bool] = []
    monkeypatch.setattr("dotfiles.app.main._launch_tui", lambda: launched.append(True))
    result = runner.invoke(cli_app, ["tui"])
    assert result.exit_code == 0
    assert launched == [True]


@pytest.mark.asyncio
async def test_dashboard_has_gradient_banner_header():
    app = MissionControlApp(ctx=make_fake_context())
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Static

        banner = app.query_one("#banner", Static)
        text = getattr(banner.render(), "plain", str(banner.render()))
        assert "█" in text


def test_dashboard_snapshot(snap_compare):
    """Golden snapshot of the booted dashboard (banner + Remote + Sessions panes)."""
    app = MissionControlApp(ctx=make_fake_context())
    assert snap_compare(app)


def test_app_real_context_respects_stdin_interactivity(monkeypatch):
    """When no ctx is injected, MissionControlApp must pass isatty() to build_real_context."""
    import contextlib
    import io
    import sys

    captured: list[bool] = []

    def fake_build(*, interactive: bool) -> None:  # type: ignore[return]
        captured.append(interactive)
        raise SystemExit(0)  # abort before the app tries to contact real system

    monkeypatch.setattr("dotfiles.tui.app.build_real_context", fake_build)

    # Simulate non-interactive stdin (pipe / mosh)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))

    with contextlib.suppress(SystemExit):
        MissionControlApp()

    assert captured == [False], "app should pass isatty()=False when stdin is not a tty"
