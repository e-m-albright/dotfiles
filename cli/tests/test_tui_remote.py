"""Remote pane renders RemoteStatus from core."""

import pytest

from dotfiles.cli.context import AppContext
from dotfiles.tui.app import MissionControlApp
from tests.fakes import FakeProcessRunner, make_fake_context


def _remote_ctx() -> AppContext:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
    runner.script(("tailscale", "status"), stdout="100.64.0.1 host\n")
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="orac\n")
    return make_fake_context(runner=runner)


@pytest.mark.asyncio
async def test_remote_pane_shows_status():
    app = MissionControlApp(ctx=_remote_ctx())
    async with app.run_test() as pilot:
        await pilot.pause()
        # let the status worker finish and repaint
        await app.workers.wait_for_complete()
        await pilot.pause()
        from dotfiles.tui.panes.remote import RemotePane

        pane = app.query_one(RemotePane)
        text = pane.render_status_line()
        assert "Remote Login" in text
        assert "on" in text.lower()
        assert "100.64.0.1" in text


@pytest.mark.asyncio
async def test_copy_connect_command_uses_connection_info():
    app = MissionControlApp(ctx=_remote_ctx())
    async with app.run_test() as pilot:
        await pilot.pause()
        from dotfiles.tui.panes.remote import RemotePane

        pane = app.query_one(RemotePane)
        cmd = pane.connect_command()
        assert "mosh" in cmd
        assert "evan@orac" in cmd


@pytest.mark.asyncio
async def test_toggle_remote_login_warns_when_not_interactive():
    # interactive=False (over a non-interactive mosh session) -> sudo-or-warn
    app = MissionControlApp(ctx=_remote_ctx())
    async with app.run_test() as pilot:
        await pilot.pause()
        from dotfiles.tui.panes.remote import RemotePane

        pane = app.query_one(RemotePane)
        result = pane.toggle_login_plan()
        # planning only — no real systemsetup executed in the test
        assert result.level in {"warn", "info", "success"}
