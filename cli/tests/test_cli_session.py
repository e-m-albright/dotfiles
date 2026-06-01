from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import FakeProcessRunner, FakeSessionLauncher, make_fake_context

runner = CliRunner()


def _ctx_with_sessions(*, selection=None):
    r = FakeProcessRunner()
    r.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 1h ago]\nwork [Created 5m ago] (current)\n",
    )
    launcher = FakeSessionLauncher(selection=selection)
    return make_fake_context(runner=r, launcher=launcher), launcher


def test_ls_lists_sessions() -> None:
    ctx, _ = _ctx_with_sessions()
    result = runner.invoke(app, ["sesh", "ls"], obj=ctx)
    assert result.exit_code == 0
    assert "mobile" in result.output
    assert "work" in result.output


def test_attach_with_name_hands_off_to_zellij() -> None:
    ctx, launcher = _ctx_with_sessions()
    result = runner.invoke(app, ["sesh", "attach", "mobile"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == [["zellij", "attach", "--create", "mobile"]]


def test_new_creates_and_attaches() -> None:
    ctx, launcher = _ctx_with_sessions()
    result = runner.invoke(app, ["sesh", "new", "scratch"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == [["zellij", "attach", "--create", "scratch"]]


def test_kill_runs_and_reports() -> None:
    ctx, _ = _ctx_with_sessions()
    result = runner.invoke(app, ["sesh", "kill", "work"], obj=ctx)
    assert result.exit_code == 0
    assert "Killed session work" in result.output


def test_bare_picker_picks_then_attaches() -> None:
    ctx, launcher = _ctx_with_sessions(selection="work")
    result = runner.invoke(app, ["sesh"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.picked == [["mobile", "work"]]
    assert launcher.attached == [["zellij", "attach", "--create", "work"]]


def test_bare_picker_cancelled_does_nothing() -> None:
    ctx, launcher = _ctx_with_sessions(selection=None)
    result = runner.invoke(app, ["sesh"], obj=ctx)
    assert result.exit_code == 0
    assert launcher.attached == []


def test_ls_reports_zellij_error() -> None:
    from tests.fakes import FakeProcessRunner, make_fake_context

    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), exit_code=1, stdout="", stderr="boom")
    result = runner.invoke(app, ["sesh", "ls"], obj=make_fake_context(runner=r))
    assert result.exit_code == 1
    assert "zellij error" in result.output


def test_bare_picker_reports_zellij_error() -> None:
    from tests.fakes import FakeProcessRunner, make_fake_context

    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), exit_code=1, stdout="", stderr="boom")
    result = runner.invoke(app, ["sesh"], obj=make_fake_context(runner=r))
    assert result.exit_code == 1
    assert "zellij error" in result.output
