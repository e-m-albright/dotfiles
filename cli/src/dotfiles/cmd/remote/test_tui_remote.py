"""Remote pane renders RemoteStatus from core."""

import pytest

from dotfiles.app.context import AppContext
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context
from dotfiles.tui.app import MissionControlApp


def _remote_ctx() -> AppContext:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
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
        from dotfiles.cmd.remote.pane import RemotePane

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
        from dotfiles.cmd.remote.pane import RemotePane

        pane = app.query_one(RemotePane)
        cmd = pane.connect_command()
        assert "mosh" in cmd
        assert "evan@orac" in cmd


@pytest.mark.asyncio
async def test_toggle_remote_login_points_to_sharing_pane():
    # The TUI never flips Remote Login — [t] just surfaces where to toggle it.
    app = MissionControlApp(ctx=_remote_ctx())
    async with app.run_test() as pilot:
        await pilot.pause()
        from dotfiles.cmd.remote.pane import RemotePane

        pane = app.query_one(RemotePane)
        result = pane.toggle_login_plan()
        assert result.level == "info"
        assert "Sharing" in result.message


def _kill_ctx() -> AppContext:
    """Context whose runner we can inspect for pkill calls."""
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("tailscale", "status"), stdout="100.64.0.1 host\n")
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="orac\n")
    return make_fake_context(runner=runner)


@pytest.mark.asyncio
async def test_kill_sessions_confirm_path_runs_pkill_not_disable():
    """Confirming [k] must call kill_sessions (pkill mosh-server) and NOT systemsetup off."""
    ctx = _kill_ctx()
    app = MissionControlApp(ctx=ctx)
    async with app.run_test() as pilot:
        await pilot.pause()
        from dotfiles.cmd.remote.pane import RemotePane

        pane = app.query_one(RemotePane)
        # Directly invoke the confirmed callback (True = user confirmed)
        pane._on_kill_confirmed(True)
        # Let any background workers finish
        await app.workers.wait_for_complete()
        await pilot.pause()

        runner = ctx.runner
        assert isinstance(runner, FakeProcessRunner)
        assert ("pkill", "-u", "evan", "mosh-server") in runner.calls
        assert ("pkill", "-u", "evan", "sshd") in runner.calls
        # Must NOT disable Remote Login
        assert ("sudo", "systemsetup", "-setremotelogin", "-f", "off") not in runner.calls


@pytest.mark.asyncio
async def test_kill_sessions_cancel_path_does_not_run_pkill():
    """Cancelling [k] (dismiss=False or None) must not call pkill at all."""
    ctx = _kill_ctx()
    app = MissionControlApp(ctx=ctx)
    async with app.run_test() as pilot:
        await pilot.pause()
        from dotfiles.cmd.remote.pane import RemotePane

        pane = app.query_one(RemotePane)

        # Test False (cancel button)
        pane._on_kill_confirmed(False)
        await app.workers.wait_for_complete()
        await pilot.pause()

        # Test None (dismissed without choice)
        pane._on_kill_confirmed(None)
        await app.workers.wait_for_complete()
        await pilot.pause()

        runner = ctx.runner
        assert isinstance(runner, FakeProcessRunner)
        assert ("pkill", "-u", "evan", "mosh-server") not in runner.calls
        assert ("pkill", "-u", "evan", "sshd") not in runner.calls
