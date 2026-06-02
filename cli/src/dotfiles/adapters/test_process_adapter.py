from dotfiles.adapters.ports import ProcessRunner
from dotfiles.adapters.process import SubprocessRunner


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


def test_subprocess_runner_pipes_input_to_stdin() -> None:
    """stdin= kwarg is passed as stdin; cat echoes it back on stdout."""
    result = SubprocessRunner().run(["cat"], stdin="hi")
    assert result.ok is True
    assert result.stdout == "hi"
