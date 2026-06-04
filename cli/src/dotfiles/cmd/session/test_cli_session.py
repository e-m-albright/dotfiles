from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.cmd.session.cli import _ls_line, _picker_row
from dotfiles.cmd.session.models import AgentActivity, Session
from dotfiles.testing.fakes import FakeProcessRunner, FakeSessionLauncher, make_fake_context

runner = CliRunner()


def _ctx_with_mobile_layout(tmp_path: Path, *, mobile_running: bool):
    """Context whose home has a deployed `mobile` layout and a scripted session list."""
    layouts = tmp_path / ".config" / "zellij" / "layouts"
    layouts.mkdir(parents=True)
    (layouts / "mobile.kdl").write_text("layout {}\n")
    listing = "mobile [Created 1h ago]\nwork (current)\n" if mobile_running else "work (current)\n"
    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), stdout=listing)
    launcher = FakeSessionLauncher()
    return make_fake_context(runner=r, launcher=launcher, home=tmp_path), launcher


def _ctx_with_sessions(*, selection=None):
    r = FakeProcessRunner()
    r.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 1h ago]\nwork [Created 5m ago] (current)\n",
    )
    launcher = FakeSessionLauncher(selection=selection)
    return make_fake_context(runner=r, launcher=launcher), launcher


def _ctx_with_exited(*, state_dir: Path | None = None):
    r = FakeProcessRunner()
    r.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout=(
            "mobile [Created 1h ago] (current)\n"
            "fresh [Created 2h ago] (EXITED - attach to resurrect)\n"
            "ancient [Created 30d ago] (EXITED - attach to resurrect)\n"
        ),
    )
    return make_fake_context(runner=r, state_dir=state_dir), r


def test_ls_runs_guarded_prune_sweep(tmp_path: Path) -> None:
    ctx, r = _ctx_with_exited(state_dir=tmp_path)
    result = runner.invoke(app, ["session", "ls"], obj=ctx)
    assert result.exit_code == 0
    # The opportunistic sweep dropped the >14d session; the stamp was written.
    assert ("zellij", "delete-session", "ancient") in r.calls
    assert (tmp_path / "session-prune").exists()


def test_ls_sweep_is_guarded_by_recent_stamp(tmp_path: Path) -> None:
    (tmp_path / "session-prune").write_text(datetime.now().isoformat())
    ctx, r = _ctx_with_exited(state_dir=tmp_path)
    runner.invoke(app, ["session", "ls"], obj=ctx)
    # Swept within the last day → no deletions this load.
    assert not any(c[:2] == ("zellij", "delete-session") for c in r.calls)


def test_prune_dry_run_lists_without_deleting() -> None:
    ctx, r = _ctx_with_exited()
    result = runner.invoke(app, ["session", "prune", "--dry-run"], obj=ctx)
    assert result.exit_code == 0
    assert "ancient" in result.output  # >14d, would be dropped
    assert "fresh" not in result.output  # within retention, kept
    assert not any(c[:2] == ("zellij", "delete-session") for c in r.calls)


def test_prune_deletes_old_keeps_recent() -> None:
    ctx, r = _ctx_with_exited()
    result = runner.invoke(app, ["session", "prune"], obj=ctx)
    assert result.exit_code == 0
    assert ("zellij", "delete-session", "ancient") in r.calls
    assert ("zellij", "delete-session", "fresh") not in r.calls
    assert "ancient" in result.output


def test_prune_reports_nothing_when_no_exited() -> None:
    ctx, _ = _ctx_with_sessions()  # only running sessions
    result = runner.invoke(app, ["session", "prune"], obj=ctx)
    assert result.exit_code == 0
    assert "No exited sessions" in result.output


def test_ls_lists_sessions() -> None:
    ctx, _ = _ctx_with_sessions()
    result = runner.invoke(app, ["session", "ls"], obj=ctx)
    assert result.exit_code == 0
    assert "mobile" in result.output
    assert "work" in result.output


def test_ls_shows_age_on_exited_rows(tmp_path: Path) -> None:
    # Guard the sweep so the row is only formatted, not deleted mid-list.

    (tmp_path / "session-prune").write_text(datetime.now().isoformat())
    ctx, _ = _ctx_with_exited(state_dir=tmp_path)
    result = runner.invoke(app, ["session", "ls"], obj=ctx)
    assert result.exit_code == 0
    assert "exited · 30d" in result.output


def _agent(name: str, cwd: str = "/home/evan/code") -> AgentActivity:
    return AgentActivity(agent=name, cwd=cwd, last_active=datetime(2026, 1, 1))


def test_ls_line_running_shows_agents_and_programs() -> None:
    s = Session(name="work", running=True, current=True)
    line = _ls_line(s, programs=["Claude Code", "nvim"], agents=[_agent("claude")])
    assert "work" in line
    assert "(current)" in line
    assert "[green]claude[/]" in line
    assert "Claude Code · nvim" in line


def test_ls_line_running_without_enrichment_is_just_name_and_state() -> None:
    s = Session(name="mobile", running=True, current=False)
    assert _ls_line(s) == "  [bold]mobile[/] [dim](running)[/]"


def test_ls_line_caps_programs_with_overflow() -> None:
    s = Session(name="busy", running=True, current=False)
    line = _ls_line(s, programs=["a", "b", "c", "d", "e"])
    assert "+2" in line


def test_ls_line_escapes_program_markup() -> None:
    s = Session(name="x", running=True, current=False)
    line = _ls_line(s, programs=["weird [title]"])
    assert "\\[title]" in line  # escaped so rich won't treat it as a tag


def test_picker_row_has_clean_key_and_enriched_label() -> None:
    s = Session(name="work", running=True, current=True)
    key, tab, label = _picker_row(s, programs=["nvim"], agents=[_agent("claude")]).partition("\t")
    assert key == "work"  # hidden field fzf returns → clean session name
    assert tab == "\t"
    # The visible label carries the same info as `ls` (ANSI-wrapped, so substrings).
    assert "claude" in label
    assert "nvim" in label


def test_ls_line_exited_is_minimal() -> None:
    s = Session(name="old", running=False, current=False, created_age_seconds=30 * 86400)
    assert _ls_line(s) == "  [bold]old[/] [dim](exited · 30d)[/]"


def test_attach_with_name_hands_off_to_zellij() -> None:
    ctx, launcher = _ctx_with_sessions()
    result = runner.invoke(app, ["session", "attach", "mobile"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == [["zellij", "attach", "--create", "mobile"]]


def test_new_creates_and_attaches() -> None:
    ctx, launcher = _ctx_with_sessions()
    result = runner.invoke(app, ["session", "new", "scratch"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == [["zellij", "attach", "--create", "scratch"]]


def test_attach_creates_with_layout_when_session_absent(tmp_path: Path) -> None:
    ctx, launcher = _ctx_with_mobile_layout(tmp_path, mobile_running=False)
    result = runner.invoke(app, ["session", "attach", "mobile"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == [["zellij", "--session", "mobile", "--layout", "mobile"]]


def test_attach_plain_when_layout_session_already_running(tmp_path: Path) -> None:
    ctx, launcher = _ctx_with_mobile_layout(tmp_path, mobile_running=True)
    result = runner.invoke(app, ["session", "attach", "mobile"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == [["zellij", "attach", "mobile"]]


def test_kill_runs_and_reports() -> None:
    ctx, _ = _ctx_with_sessions()
    result = runner.invoke(app, ["session", "kill", "work"], obj=ctx)
    assert result.exit_code == 0
    assert "Killed session work" in result.output


def test_bare_picker_picks_then_attaches() -> None:
    ctx, launcher = _ctx_with_sessions(selection="work")
    result = runner.invoke(app, ["session"], obj=ctx)
    assert result.exit_code == 0
    # Keys are the session names (current first, then by name); the fzf labels are
    # the enriched rows. The chosen key flows straight into the attach command.
    assert launcher.picked == [["work", "mobile"]]
    assert launcher.attached == [["zellij", "attach", "--create", "work"]]


def test_bare_picker_cancelled_does_nothing() -> None:
    ctx, launcher = _ctx_with_sessions(selection=None)
    result = runner.invoke(app, ["session"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == []


def test_ls_reports_zellij_error() -> None:
    from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), exit_code=1, stdout="", stderr="boom")
    result = runner.invoke(app, ["session", "ls"], obj=make_fake_context(runner=r))
    assert result.exit_code == 1
    assert "zellij error" in result.output


def test_bare_picker_reports_zellij_error() -> None:
    from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), exit_code=1, stdout="", stderr="boom")
    result = runner.invoke(app, ["session"], obj=make_fake_context(runner=r))
    assert result.exit_code == 1
    assert "zellij error" in result.output
