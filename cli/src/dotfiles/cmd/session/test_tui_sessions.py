"""Sessions pane lists zellij sessions and resolves the attach/switch command."""

import pytest

from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context
from dotfiles.tui.app import MissionControlApp
from dotfiles.tui.launcher import zellij_handoff_command


def test_zellij_handoff_attaches_when_not_in_zellij():
    assert zellij_handoff_command("mobile", in_zellij=False) == (
        "zellij",
        "attach",
        "--create",
        "mobile",
    )


def test_zellij_handoff_switches_when_inside_zellij():
    assert zellij_handoff_command("mobile", in_zellij=True) == (
        "zellij",
        "action",
        "switch-session",
        "mobile",
    )


@pytest.mark.asyncio
async def test_sessions_pane_lists_sessions():
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [created]\nwork (current)\n",
    )
    app = MissionControlApp(ctx=make_fake_context(runner=runner))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        assert pane.session_names() == ["mobile", "work"]
