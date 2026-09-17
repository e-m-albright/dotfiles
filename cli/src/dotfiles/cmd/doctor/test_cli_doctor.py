"""Tests for the `dotfiles doctor` Typer command."""

from pathlib import Path
from types import SimpleNamespace

import pytest
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


def test_doctor_fix_workbench_hint_only_when_not_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--fix points to the agent-config reconciler only when the Workbench row needs it."""
    home = tmp_path / "home"
    home.mkdir()
    ctx = make_fake_context(home=home, dotfiles_dir=tmp_path / "dotfiles")
    # No workbench binary anywhere -> the Workbench row is "missing" -> hint shows.
    # (DoctorService binds shutil.which at class definition, so inject via wrapper.)
    from dotfiles.cmd.doctor import cli as doctor_cli

    real_service = doctor_cli.DoctorService
    monkeypatch.setattr(
        doctor_cli,
        "DoctorService",
        lambda **kwargs: real_service(**{**kwargs, "which": lambda _name: None}),
    )
    result = runner.invoke(app, ["doctor", "--fix"], obj=ctx)
    assert "workbench sync" in result.output


@pytest.mark.parametrize(
    ("check", "expected"),
    [
        (
            {"section": "Runtime", "name": "Node", "status": "warn"},
            "1 warning(s)",
        ),
        (
            {"section": "Runtime", "name": "Node", "status": "ok"},
            "All checks passed",
        ),
    ],
)
def test_doctor_renders_nonfailure_outcomes(
    monkeypatch: pytest.MonkeyPatch, check: dict[str, str], expected: str
) -> None:
    from dotfiles.cmd.doctor import cli as doctor_cli
    from dotfiles.cmd.doctor.models import CheckResult

    service = SimpleNamespace(run=lambda: [CheckResult(**check)])
    monkeypatch.setattr(doctor_cli, "DoctorService", lambda **_kwargs: service)

    result = runner.invoke(app, ["doctor"], obj=make_fake_context())

    assert result.exit_code == 0
    assert expected in result.output
