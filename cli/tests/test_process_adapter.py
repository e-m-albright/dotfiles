from dotfiles_cli.adapters.process import SubprocessRunner
from dotfiles_cli.core.ports import ProcessRunner


def test_subprocess_runner_satisfies_port() -> None:
    assert isinstance(SubprocessRunner(), ProcessRunner)


def test_runs_echo_and_captures_stdout() -> None:
    result = SubprocessRunner().run(["echo", "hello"])
    assert result.ok is True
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0


def test_nonzero_exit_is_captured_not_raised_by_default() -> None:
    result = SubprocessRunner().run(["false"])
    assert result.ok is False
    assert result.exit_code != 0


def test_check_true_raises_on_failure() -> None:
    import subprocess

    import pytest

    with pytest.raises(subprocess.CalledProcessError):
        SubprocessRunner().run(["false"], check=True)
