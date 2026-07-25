"""Remote pane renders phone-access RemoteStatus from core."""

import pytest

from dotfiles.app.context import AppContext
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context


def _remote_ctx() -> AppContext:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "status"), stdout="100.64.0.1 host\n")
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="orac\n")
    return make_fake_context(runner=runner)


@pytest.mark.asyncio
async def test_remote_pane_shows_status():
    from dotfiles.tui.app import MissionControlApp

    app = MissionControlApp(ctx=_remote_ctx())
    async with app.run_test() as pilot:
        await pilot.pause()
        # let the status worker finish and repaint
        await app.workers.wait_for_complete()
        await pilot.pause()
        from dotfiles.cmd.remote.pane import RemotePane

        pane = app.query_one(RemotePane)
        text = pane.render_status_line()
        assert "Tailscale" in text
        assert "100.64.0.1" in text
        assert "orac" in text
        assert "Zellij web" in text


@pytest.mark.asyncio
async def test_copy_connect_command_uses_paseo_addr():
    from dotfiles.tui.app import MissionControlApp

    app = MissionControlApp(ctx=_remote_ctx())
    async with app.run_test() as pilot:
        await pilot.pause()
        from dotfiles.cmd.remote.pane import RemotePane

        pane = app.query_one(RemotePane)
        cmd = pane.connect_command()
        # The copy action yields the Paseo daemon address (tailnet IP:port).
        assert cmd == "100.64.0.1:6767"
