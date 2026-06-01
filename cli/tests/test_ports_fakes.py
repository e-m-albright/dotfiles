from dotfiles.core.ports import ProcessRunner
from tests.fakes import FakeProcessRunner


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


def test_fake_runner_honors_check_true_on_failure() -> None:
    import subprocess

    import pytest

    runner = FakeProcessRunner()
    runner.script(("false",), exit_code=1, stderr="boom")
    with pytest.raises(subprocess.CalledProcessError):
        runner.run(["false"], check=True)


def test_fake_runner_check_true_ok_when_success() -> None:
    runner = FakeProcessRunner()
    runner.script(("true",), exit_code=0)
    result = runner.run(["true"], check=True)
    assert result.ok is True


def test_fake_runner_records_input() -> None:
    runner = FakeProcessRunner()
    runner.run(["pbcopy"], stdin="hello clipboard")
    assert runner.inputs == ["hello clipboard"]
    assert runner.calls_with_input == [(("pbcopy",), "hello clipboard")]


def test_fake_runner_records_none_input_by_default() -> None:
    runner = FakeProcessRunner()
    runner.run(["echo", "hi"])
    assert runner.inputs == [None]
