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
        # Current session is surfaced first within the ACTIVE group.
        assert pane.session_names() == ["work", "mobile"]


def test_session_action_buttons_vary_by_state():
    from dotfiles.cmd.session.models import Session
    from dotfiles.cmd.session.pane import session_action_buttons

    running = Session(name="work", running=True, current=False)
    current = Session(name="mobile", running=True, current=True)
    exited = Session(name="old", running=False, current=False)

    assert [b[1] for b in session_action_buttons(running)] == ["attach", "kill", "cancel"]
    # The session you're in offers no destructive action (would tear down the TUI).
    assert [b[1] for b in session_action_buttons(current)] == ["cancel"]
    assert [b[1] for b in session_action_buttons(exited)] == ["attach", "delete", "cancel"]


def _app_with(stdout: str):
    runner = FakeProcessRunner()
    runner.script(("zellij", "list-sessions", "--no-formatting"), stdout=stdout)
    return MissionControlApp(ctx=make_fake_context(runner=runner)), runner


@pytest.mark.asyncio
async def test_new_binding_opens_create_modal():
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.pane import _NewSession

        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, _NewSession)


@pytest.mark.asyncio
async def test_selecting_session_row_opens_action_sheet():
    app, _ = _app_with("work [created]\n")  # running, not current
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import SessionsPane, _SessionActions

        view = app.query_one("#session-list", ListView)
        target = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        view.index = target
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, _SessionActions)
        # Confirm the kill action is dispatched and triggers a reload.
        pane = app.query_one(SessionsPane)
        session = next(s for s in pane._sessions if s.name == "work")
        pane._on_action(session, "kill")
        await pilot.pause()


@pytest.mark.asyncio
async def test_kill_action_invokes_kill_session():
    app, runner = _app_with("work [created]\nold (EXITED - attach to resurrect)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        pane._on_action(Session(name="work", running=True, current=False), "kill")
        pane._on_action(Session(name="old", running=False, current=False), "delete")
        await pilot.pause()
        assert ("zellij", "kill-session", "work") in runner.calls
        assert ("zellij", "delete-session", "old") in runner.calls


@pytest.mark.asyncio
async def test_sessions_pane_groups_active_and_resurrectable():
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="work (current)\nold (EXITED - attach to resurrect)\n",
    )
    app = MissionControlApp(ctx=make_fake_context(runner=runner))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListItem, ListView

        view = app.query_one("#session-list", ListView)
        headers = [i for i in view.query(ListItem) if "section-header" in i.classes]
        rows = [i for i in view.query(ListItem) if "session-row" in i.classes]
        # Two group headers (ACTIVE + RESURRECTABLE), one selectable row each.
        assert len(headers) == 2
        assert {i.id for i in rows} == {"sess-work", "sess-old"}
        # The exited row carries the resurrectable accent class and is enabled (tappable).
        old_row = next(i for i in rows if i.id == "sess-old")
        assert "is-exited" in old_row.classes
        # Headers are non-selectable so taps can't misfire on them.
        assert all(h.disabled for h in headers)
