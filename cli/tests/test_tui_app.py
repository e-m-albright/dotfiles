"""Mission Control TUI app boots and mounts panes."""

import pytest
from typer.testing import CliRunner

from dotfiles.cli.main import app as cli_app
from dotfiles.tui.app import MissionControlApp
from tests.fakes import make_fake_context

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
    monkeypatch.setattr("dotfiles.cli.main._launch_tui", lambda: launched.append(True))
    result = runner.invoke(cli_app, ["tui"])
    assert result.exit_code == 0
    assert launched == [True]


def test_dashboard_snapshot(snap_compare):
    """Golden snapshot of the booted dashboard (Remote + Sessions panes)."""
    app = MissionControlApp(ctx=make_fake_context())
    assert snap_compare(app)
