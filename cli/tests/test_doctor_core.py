"""Tests for DoctorService core logic."""

from pathlib import Path

from dotfiles_cli.core.doctor import DoctorService
from dotfiles_cli.core.models import CheckResult
from tests.fakes import FakeFileSystem, FakeProcessRunner


def _svc(runner=None, fs=None, *, fix=False, which=None):
    return DoctorService(
        runner=runner or FakeProcessRunner(),
        fs=fs or FakeFileSystem(),
        home=Path("/home/evan"),
        dotfiles_dir=Path("/home/evan/dotfiles"),
        fix=fix,
        which=which or (lambda _name: None),
    )


def test_check_result_fields() -> None:
    c = CheckResult(section="Core Tools", name="Git", status="ok", detail="git 2.4", hint="")
    assert c.status == "ok"
    assert c.is_failure is False
    assert (
        CheckResult(section="x", name="y", status="missing", hint="brew install y").is_failure
        is True
    )
    assert CheckResult(section="x", name="y", status="warn").is_failure is False


def test_tool_present_and_absent() -> None:
    runner = FakeProcessRunner()
    runner.script(("git", "--version"), stdout="git version 2.43\n")
    svc = _svc(runner, which=lambda n: "/usr/bin/git" if n == "git" else None)
    ok = svc._tool("Core Tools", "Git", "git", "brew install git")
    assert ok.status == "ok"
    assert "2.43" in ok.detail
    missing = svc._tool("Core Tools", "Nope", "nope-bin", "install nope")
    assert missing.status == "missing"
    assert missing.hint == "install nope"


def test_app_bundle_check() -> None:
    fs = FakeFileSystem()
    fs.mkdir(Path("/Applications/Termius.app"))
    svc = _svc(fs=fs)
    present = svc._app(
        "Remote Shell", "Termius", Path("/Applications/Termius.app"), "brew install --cask termius"
    )
    assert present.status == "ok"
    absent = svc._app("Editors", "Ghost", Path("/Applications/Ghost.app"), "hint")
    assert absent.status == "missing"


def test_symlink_check_and_fix() -> None:
    src = Path("/home/evan/dotfiles/shell/.zshrc")
    dest = Path("/home/evan/.zshrc")
    fs = FakeFileSystem()
    # not linked -> missing without fix
    assert _svc(fs=fs)._symlink("Configuration", ".zshrc", src, dest).status == "missing"
    # with fix -> creates link, status fixed
    fs2 = FakeFileSystem()
    res = _svc(fs=fs2, fix=True)._symlink("Configuration", ".zshrc", src, dest)
    assert res.status == "fixed"
    assert fs2.is_symlink(dest)
    # already linked -> ok
    fs3 = FakeFileSystem()
    fs3.symlink(src, dest)
    assert _svc(fs=fs3)._symlink("Configuration", ".zshrc", src, dest).status == "ok"
