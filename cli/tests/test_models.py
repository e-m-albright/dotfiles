from dotfiles_cli.core.models import CommandResult


def test_command_result_ok_is_true_for_zero_exit() -> None:
    result = CommandResult(command=("echo", "hi"), exit_code=0, stdout="hi\n", stderr="")
    assert result.ok is True


def test_command_result_ok_is_false_for_nonzero_exit() -> None:
    result = CommandResult(command=("false",), exit_code=1, stdout="", stderr="boom")
    assert result.ok is False


def test_command_result_is_immutable() -> None:
    import pydantic
    import pytest

    result = CommandResult(command=("echo",), exit_code=0, stdout="", stderr="")
    with pytest.raises(pydantic.ValidationError):
        result.exit_code = 2  # type: ignore[misc]
