from datetime import datetime
from pathlib import Path

from dotfiles_cli.core.ports import Clock, FileSystem, ProcessRunner
from tests.fakes import FakeClock, FakeFileSystem, FakeProcessRunner


def test_fake_runner_returns_scripted_result_and_records_calls() -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")

    result = runner.run(["systemsetup", "-getremotelogin"])

    assert isinstance(runner, ProcessRunner)
    assert result.ok is True
    assert "Remote Login: On" in result.stdout
    assert runner.calls == [("systemsetup", "-getremotelogin")]


def test_fake_runner_defaults_to_empty_success() -> None:
    runner = FakeProcessRunner()
    result = runner.run(["anything"])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_fake_filesystem_roundtrips() -> None:
    fs = FakeFileSystem()
    assert isinstance(fs, FileSystem)
    p = Path("/home/u/.ssh/authorized_keys")
    assert fs.exists(p) is False
    fs.mkdir(p.parent)
    fs.write_text(p, "ssh-ed25519 AAAA test\n")
    assert fs.exists(p) is True
    assert fs.read_text(p) == "ssh-ed25519 AAAA test\n"


def test_fake_clock_is_fixed() -> None:
    clock = FakeClock(datetime(2026, 5, 31, 12, 0, 0))
    assert isinstance(clock, Clock)
    assert clock.now() == datetime(2026, 5, 31, 12, 0, 0)
