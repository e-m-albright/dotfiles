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

    assert [b[1] for b in session_action_buttons(running)] == ["attach", "kill", "cancel"]
    # The session you're in offers no destructive action (would tear down the TUI).
    assert [b[1] for b in session_action_buttons(current)] == ["cancel"]


def test_live_sessions_keeps_running_current_first():
    from dotfiles.cmd.session.models import Session
    from dotfiles.cmd.session.pane import live_sessions

    sessions = [
        Session(name="mobile", running=True, current=False),
        Session(name="old", running=False, current=False),  # exited -> dropped
        Session(name="work", running=True, current=True),
    ]
    assert [s.name for s in live_sessions(sessions)] == ["work", "mobile"]


def _app_with(stdout: str):
    runner = FakeProcessRunner()
    runner.script(("zellij", "list-sessions", "--no-formatting"), stdout=stdout)
    return MissionControlApp(ctx=make_fake_context(runner=runner)), runner


@pytest.mark.asyncio
async def test_create_requests_handoff_instead_of_exec(monkeypatch):
    # Handoff must go through request_handoff (exit-then-exec), never exec inside
    # the running app — otherwise the new session inherits a tty that eats input.
    monkeypatch.delenv("ZELLIJ", raising=False)
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        pane._on_new_session("api")
        assert app.handoff_command == ("zellij", "attach", "--create", "api")


@pytest.mark.asyncio
async def test_attach_action_requests_handoff(monkeypatch):
    monkeypatch.delenv("ZELLIJ", raising=False)
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        pane._on_action(Session(name="work", running=True, current=False), "attach")
        assert app.handoff_command == ("zellij", "attach", "--create", "work")


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
    app, runner = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        pane._on_action(Session(name="work", running=True, current=False), "kill")
        await pilot.pause()
        assert ("zellij", "kill-session", "work") in runner.calls


@pytest.mark.asyncio
async def test_kill_hotkey_confirms_then_kills_highlighted_session():
    app, runner = _app_with("work [created]\n")  # running, not current
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import _ConfirmKill

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        await pilot.press("k")
        await pilot.pause()
        assert isinstance(app.screen, _ConfirmKill)
        await pilot.press("enter")  # confirm the highlighted "Kill" button
        await pilot.pause()
        assert ("zellij", "kill-session", "work") in runner.calls


@pytest.mark.asyncio
async def test_kill_hotkey_refuses_current_session():
    app, runner = _app_with("work (current)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.screen import ModalScreen
        from textual.widgets import ListView

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        await pilot.press("k")
        await pilot.pause()
        # No confirm sheet opens, and nothing is killed (would tear down the TUI).
        assert not isinstance(app.screen, ModalScreen)
        assert not any(c[:2] == ("zellij", "kill-session") for c in runner.calls)


@pytest.mark.asyncio
async def test_kill_hotkey_noops_on_new_row():
    app, runner = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.screen import ModalScreen
        from textual.widgets import ListView

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "new-session")
        await pilot.press("k")
        await pilot.pause()
        assert not isinstance(app.screen, ModalScreen)
        assert not any(c[:2] == ("zellij", "kill-session") for c in runner.calls)


@pytest.mark.asyncio
async def test_reload_twice_does_not_duplicate_new_row():
    # clear() is deferred in Textual, so a naive clear()+append() re-adds the
    # fixed-id "new-session" row before the old one is removed -> DuplicateIds.
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListItem, ListView

        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        pane.action_reload()
        await pilot.pause()
        await pilot.pause()
        view = app.query_one("#session-list", ListView)
        new_rows = [i for i in view.query(ListItem) if "new-row" in i.classes]
        assert len(new_rows) == 1


@pytest.mark.asyncio
async def test_exited_sessions_are_not_listed():
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

        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        assert pane.session_names() == ["work"]  # exited "old" filtered out
        view = app.query_one("#session-list", ListView)
        rows = {i.id for i in view.query(ListItem) if "session-row" in i.classes}
        assert rows == {"sess-work"}
