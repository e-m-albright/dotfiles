"""Tests for the `dotfiles doctor` Typer command."""

from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import make_fake_context

# NO_COLOR + wide terminal: CI forces color, which makes Rich split flag names
# with ANSI codes and breaks plain-substring help assertions (see agent setup).
runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "200"})


def test_doctor_runs_and_groups(monkeypatch) -> None:
    """Bare fake context → missing tools → exit 1, section headers printed."""
    ctx = make_fake_context()  # bare machine: nothing installed
    result = runner.invoke(app, ["doctor"], obj=ctx)
    assert result.exit_code == 1
    assert "Core Tools" in result.output


def test_doctor_help_has_fix_flag() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "--fix" in result.output


def test_doctor_fix_prints_agent_setup_hint(tmp_path: Path) -> None:
    """--fix output must contain the agent-setup hint."""
    home = tmp_path / "home"
    home.mkdir()
    ctx = make_fake_context(home=home, dotfiles_dir=tmp_path / "dotfiles")
    result = runner.invoke(app, ["doctor", "--fix"], obj=ctx)
    assert "dotfiles agent setup" in result.output


# The "all checks pass → no failures" scenario is covered as a direct
# DoctorService unit test in test_doctor_core.py::test_run_all_present_has_no_failure,
# where the system paths (/Applications, /opt/homebrew/bin) are injected under
# tmp_path. Re-testing it through the CLI added nothing but a host-dependent,
# mock-heavy duplicate, so it lives at the service layer instead.
