"""Sessions pane lists zellij sessions and resolves the attach/switch command."""

import sys

import pytest

from dotfiles.cmd.session.zellij import zellij_cache_root
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context
from dotfiles.tui.app import MissionControlApp


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
        from textual.widgets import ListView

        # Current session is surfaced first within the ACTIVE group.
        view = app.query_one("#session-list", ListView)
        ids = [item.id for item in view.children if item.id and item.id.startswith("sess-")]
        assert ids == ["sess-work", "sess-mobile"]


def test_action_sheet_snapshot(snap_compare, monkeypatch):
    """Golden snapshot of the action sheet: brand button colors + aligned text."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    runner = FakeProcessRunner()
    runner.script(("zellij", "list-sessions", "--no-formatting"), stdout="work [created]\n")
    app = MissionControlApp(ctx=make_fake_context(runner=runner))

    async def run_before(pilot):
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        view = pilot.app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(app, run_before=run_before)


def test_session_action_buttons_vary_by_state():
    from dotfiles.cmd.session.models import Session
    from dotfiles.cmd.session.pane import session_action_buttons

    running = Session(name="work", running=True, current=False)
    current = Session(name="mobile", running=True, current=True)

    exited = Session(name="old", running=False, current=False, created_age_seconds=99)

    assert [b[1] for b in session_action_buttons(running)] == ["attach", "kill", "cancel"]
    # The session you're in offers no destructive action (would tear down the TUI).
    assert [b[1] for b in session_action_buttons(current)] == ["cancel"]
    # Exited sessions are resurrectable or deletable, not attach/kill.
    assert [b[1] for b in session_action_buttons(exited)] == ["resurrect", "delete", "cancel"]


def test_live_sessions_keeps_running_current_first():
    from dotfiles.cmd.session.models import Session
    from dotfiles.cmd.session.service import live_sessions

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
async def test_vim_jk_move_the_list_highlight():
    # j/k move the highlight (mobile-friendly arrow alternative); after one j the
    # second live row ("work") is highlighted and Enter opens its action sheet.
    app, _ = _app_with("mobile [created]\nwork [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import _SessionActions

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-mobile")
        await pilot.press("j")  # down to the next session row
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, _SessionActions)
        assert app.screen._s.name == "work"


@pytest.mark.asyncio
async def test_numeric_hotkey_jumps_to_nth_live_session(monkeypatch):
    # 1-9 attach the n-th live session (current first, then by name) — keyboard/
    # mobile session switching without tapping or scrolling.
    monkeypatch.delenv("ZELLIJ", raising=False)
    app, _ = _app_with("mobile [created]\nwork (current)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        # Live order: current ("work") first, then "mobile" → 2 jumps to mobile.
        await pilot.press("2")
        await pilot.pause()
        assert app.handoff_command == ("zellij", "attach", "--create", "mobile")


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
async def test_tui_reload_never_prunes_resurrectable_sessions():
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout=("mobile (current)\nancient [Created 30d ago] (EXITED - attach to resurrect)\n"),
    )
    app = MissionControlApp(ctx=make_fake_context(runner=runner))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        assert not any(c[:2] == ("zellij", "delete-session") for c in runner.calls)


@pytest.mark.asyncio
async def test_resurrect_action_requests_handoff(monkeypatch):
    monkeypatch.delenv("ZELLIJ", raising=False)
    app, _ = _app_with("old [Created 2d ago] (EXITED - attach to resurrect)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        exited = Session(name="old", running=False, current=False, created_age_seconds=2 * 86400)
        pane._on_action(exited, "resurrect")
        # Attaching to an exited session resurrects it from serialized state.
        assert app.handoff_command == ("zellij", "attach", "--create", "old")


@pytest.mark.asyncio
async def test_delete_action_invokes_delete_session():
    app, runner = _app_with("old [Created 2d ago] (EXITED - attach to resurrect)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        exited = Session(name="old", running=False, current=False, created_age_seconds=2 * 86400)
        pane._on_action(exited, "delete")
        await pilot.pause()
        assert ("zellij", "delete-session", "old") in runner.calls


@pytest.mark.asyncio
async def test_exited_row_resurrect_hotkey(monkeypatch):
    monkeypatch.delenv("ZELLIJ", raising=False)
    app, _ = _app_with("old [Created 2d ago] (EXITED - attach to resurrect)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import _SessionActions

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-old")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, _SessionActions)
        await pilot.press("r")  # resurrect hotkey
        await pilot.pause()
        assert app.handoff_command == ("zellij", "attach", "--create", "old")


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
async def test_new_session_modal_prevents_spaces_and_shows_error():
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import Input, Label

        from dotfiles.cmd.session.pane import _NewSession

        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, _NewSession)
        field = app.screen.query_one("#new-name", Input)
        assert field.placeholder == "e.g. api"
        await pilot.click("#new-name")
        await pilot.press(*"two words")
        await pilot.pause()

        assert field.value == "twowords"
        error = app.screen.query_one("#name-error", Label)
        text = getattr(error.render(), "plain", "")
        assert "Session name cannot contain spaces" in text
        await pilot.press("enter")
        await pilot.pause()
        assert app.handoff_command == ("zellij", "attach", "--create", "twowords")


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
async def test_action_sheet_hotkeys_attach_and_cancel(monkeypatch):
    monkeypatch.delenv("ZELLIJ", raising=False)
    app, _ = _app_with("work [created]\n")  # running, not current
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import _SessionActions

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, _SessionActions)
        await pilot.press("a")  # attach hotkey
        await pilot.pause()
        assert app.handoff_command == ("zellij", "attach", "--create", "work")


@pytest.mark.asyncio
async def test_action_sheet_kill_hotkey_inert_for_current_session():
    # `k`/`a` must not kill or attach the session you're already in — that
    # would tear down the TUI. Only Cancel is offered; escape dismisses.
    app, runner = _app_with("work (current)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import _SessionActions

        view = app.query_one("#session-list", ListView)
        view.index = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, _SessionActions)
        await pilot.press("k")  # inert for the current session
        await pilot.pause()
        assert isinstance(app.screen, _SessionActions)  # still open, nothing dismissed
        assert not any(c[:2] == ("zellij", "kill-session") for c in runner.calls)
        await pilot.press("escape")
        await pilot.pause()
        from textual.screen import ModalScreen

        assert not isinstance(app.screen, ModalScreen)


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
        await pilot.press("x")  # pane kill hotkey (k is vim-up now)
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
        await pilot.press("x")
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
        await pilot.press("x")
        await pilot.pause()
        assert not isinstance(app.screen, ModalScreen)
        assert not any(c[:2] == ("zellij", "kill-session") for c in runner.calls)


@pytest.mark.asyncio
async def test_rebuild_does_not_duplicate_new_row():
    # clear() is deferred in Textual, so a naive clear()+append() re-adds the
    # fixed-id "new-session" row before the old one is removed -> DuplicateIds.
    # Drive two rebuilds with *changing* data so the rebuild path is exercised.
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from datetime import datetime

        from textual.widgets import ListItem, ListView

        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        now = datetime.now()
        await pane._apply_sessions([Session(name="a", running=True, current=False)], [], now)
        await pilot.pause()
        await pane._apply_sessions([Session(name="b", running=True, current=False)], [], now)
        await pilot.pause()
        view = app.query_one("#session-list", ListView)
        new_rows = [i for i in view.query(ListItem) if "new-row" in i.classes]
        assert len(new_rows) == 1


@pytest.mark.asyncio
async def test_agent_matched_by_session_env_shows_on_row():
    # A codex process whose ZELLIJ_SESSION_NAME is 'work' shows as a badge on that
    # row — and NOT in the elsewhere line. No cwd involved.
    app, runner = _app_with("work (current)\n")
    runner.script(("pgrep", "-x", "codex"), stdout="999\n")
    runner.script(
        ("ps", "eww", "-p", "999", "-o", "command="),
        stdout="codex PWD=/Users/dev/proj ZELLIJ_SESSION_NAME=work\n",
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import Label, ListView, Static

        view = app.query_one("#session-list", ListView)
        row = next(i for i in view.children if i.id == "sess-work")
        row_text = getattr(row.query_one(Label).render(), "plain", "")
        assert "codex" in row_text
        elsewhere = getattr(app.query_one("#active-agents", Static).render(), "plain", "")
        assert "codex" not in elsewhere


@pytest.mark.asyncio
async def test_unmatched_agent_shows_in_elsewhere_line():
    app, _ = _app_with("work (current)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import Static

        from dotfiles.cmd.session.models import AgentActivity, Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        agent = AgentActivity(agent="claude", session=None, cwd="/Users/dev/public")
        await pane._apply_sessions([Session(name="work", running=True, current=True)], [agent])
        await pilot.pause()
        line = getattr(app.query_one("#active-agents", Static).render(), "plain", "")
        assert "elsewhere" in line
        assert "claude" in line
        assert "public" in line


@pytest.mark.asyncio
async def test_unchanged_matched_agents_do_not_rebuild_row():
    # The row keys on agent names; an identical refresh must not flash the list.
    app, _ = _app_with("work (created)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.models import AgentActivity, Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        sess = [Session(name="work", running=True, current=False)]
        agents = [AgentActivity(agent="claude", session="work", cwd="/x")]
        await pane._apply_sessions(sess, [], None, None, {"work": agents})
        await pilot.pause()
        view = app.query_one("#session-list", ListView)
        before = next(i for i in view.children if i.id == "sess-work")
        await pane._apply_sessions(sess, [], None, None, {"work": agents})
        await pilot.pause()
        after = next(i for i in view.children if i.id == "sess-work")
        assert before is after  # same widget -> no rebuild -> no flash


@pytest.mark.asyncio
async def test_exited_age_tick_does_not_rebuild_rows():
    # zellij reports exited age down to the second, so it changes every refresh.
    # That must NOT churn the list (would flash); only the session *set* matters.
    app, _ = _app_with("old [Created 1m ago] (EXITED - attach to resurrect)\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from datetime import datetime

        from textual.widgets import ListView

        from dotfiles.cmd.session.models import Session
        from dotfiles.cmd.session.pane import SessionsPane

        pane = app.query_one(SessionsPane)
        now = datetime.now()
        await pane._apply_sessions(
            [Session(name="old", running=False, current=False, created_age_seconds=100)], [], now
        )
        await pilot.pause()
        view = app.query_one("#session-list", ListView)
        before = next(i for i in view.children if i.id == "sess-old")
        await pane._apply_sessions(
            [Session(name="old", running=False, current=False, created_age_seconds=104)], [], now
        )
        await pilot.pause()
        after = next(i for i in view.children if i.id == "sess-old")
        assert before is after  # same widget object -> no teardown -> no flash


@pytest.mark.asyncio
async def test_unchanged_reload_does_not_rebuild_rows():
    # The auto-refresh flashed because it tore down + rebuilt the list every
    # tick. An unchanged reload must reuse the existing row widgets (identity).
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import SessionsPane

        view = app.query_one("#session-list", ListView)
        before = next(i for i in view.children if i.id == "sess-work")
        app.query_one(SessionsPane).action_reload()
        await pilot.pause()
        await pilot.pause()
        after = next(i for i in view.children if i.id == "sess-work")
        assert before is after  # same widget object -> no teardown -> no flash


@pytest.mark.asyncio
async def test_reload_preserves_highlighted_row():
    # Auto-refresh must not yank the cursor back to the top every tick.
    app, _ = _app_with("work [created]\n")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListView

        from dotfiles.cmd.session.pane import SessionsPane

        view = app.query_one("#session-list", ListView)
        target = next(i for i, item in enumerate(view.children) if item.id == "sess-work")
        view.index = target
        await pilot.pause()
        app.query_one(SessionsPane).action_reload()
        await pilot.pause()
        await pilot.pause()
        assert view.highlighted_child is not None
        assert view.highlighted_child.id == "sess-work"


@pytest.mark.asyncio
async def test_session_row_previews_running_programs(tmp_path):
    # zellij's session_info cache says what's running; the row should preview it.
    # Write to the cache root for THIS platform (macOS Library/Caches vs Linux
    # XDG ~/.cache) so the test is hermetic on the CI runner, not just macOS.
    info = (
        zellij_cache_root(tmp_path, sys.platform) / "contract_version_1" / "session_info" / "work"
    )
    info.mkdir(parents=True)
    (info / "session-metadata.kdl").write_text(
        'panes {\n    pane { id 0 is_plugin false exited false title "nvim" }\n}\n'
    )
    runner = FakeProcessRunner()
    runner.script(("zellij", "list-sessions", "--no-formatting"), stdout="work [created]\n")
    app = MissionControlApp(ctx=make_fake_context(runner=runner, home=tmp_path))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import Label, ListView

        view = app.query_one("#session-list", ListView)
        row = next(i for i in view.children if i.id == "sess-work")
        rendered = row.query_one(Label).render()
        plain = getattr(rendered, "plain", str(rendered))
        assert "nvim" in plain


@pytest.mark.asyncio
async def test_exited_sessions_listed_as_resurrectable():
    runner = FakeProcessRunner()
    runner.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="work (current)\nold [Created 2d ago] (EXITED - attach to resurrect)\n",
    )
    app = MissionControlApp(ctx=make_fake_context(runner=runner))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import ListItem, ListView

        view = app.query_one("#session-list", ListView)
        rows = {i.id for i in view.query(ListItem) if "session-row" in i.classes}
        assert rows == {"sess-work", "sess-old"}
