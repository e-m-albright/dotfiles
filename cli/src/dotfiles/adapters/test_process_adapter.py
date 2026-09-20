import pytest

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

    with pytest.raises(subprocess.CalledProcessError):
        SubprocessRunner().run(["false"], check=True)


def test_subprocess_runner_pipes_input_to_stdin() -> None:
    """stdin= kwarg is passed as stdin; cat echoes it back on stdout."""
    result = SubprocessRunner().run(["cat"], stdin="hi")
    assert result.ok is True
    assert result.stdout == "hi"


def test_subprocess_runner_can_inherit_terminal_output(
    capfd: pytest.CaptureFixture[str],
) -> None:
    result = SubprocessRunner().run(["echo", "prompt"], capture_output=False)

    assert result.ok is True
    assert result.stdout == ""
    assert capfd.readouterr().out.strip() == "prompt"


@pytest.mark.parametrize("check", [False, True])
@pytest.mark.parametrize(
    ("failure", "code"), [("missing", 127), ("permission", 126), ("timeout", 124)]
)
def test_launch_failures_are_command_results(tmp_path, failure, code, check):
    import subprocess
    import sys

    executable = tmp_path / "command"
    kwargs = {}
    command = [str(executable)]
    if failure == "permission":
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o600)
    elif failure == "timeout":
        command = [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(5)"]
        kwargs["timeout"] = 1
    if check:
        with pytest.raises(subprocess.CalledProcessError) as raised:
            SubprocessRunner().run(command, check=True, **kwargs)
        assert raised.value.returncode == code
        assert raised.value.stderr
    else:
        result = SubprocessRunner().run(command, **kwargs)
        assert result.exit_code == code
        assert result.stderr
        if failure == "timeout":
            assert result.stdout == "started\n"
