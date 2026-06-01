"""Tests for DoctorService core logic."""

from dotfiles_cli.core.models import CheckResult


def test_check_result_fields() -> None:
    c = CheckResult(section="Core Tools", name="Git", status="ok", detail="git 2.4", hint="")
    assert c.status == "ok"
    assert c.is_failure is False
    assert (
        CheckResult(section="x", name="y", status="missing", hint="brew install y").is_failure
        is True
    )
    assert CheckResult(section="x", name="y", status="warn").is_failure is False
