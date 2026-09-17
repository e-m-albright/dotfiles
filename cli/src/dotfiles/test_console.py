from io import StringIO

import pytest
import typer
from rich.console import Console

from dotfiles.console import console, render_and_exit
from dotfiles.result import StepResult


def test_console_is_rich() -> None:
    assert isinstance(console, Console)


def test_render_and_exit_returns_for_success() -> None:
    output = StringIO()
    render_and_exit(
        Console(file=output, force_terminal=False),
        [StepResult(level="success", message="done")],
    )
    assert "done" in output.getvalue()


def test_render_and_exit_raises_requested_code_for_error() -> None:
    output = StringIO()
    with pytest.raises(typer.Exit) as raised:
        render_and_exit(
            Console(file=output, force_terminal=False),
            [StepResult(level="error", message="failed")],
            code=7,
        )
    assert raised.value.exit_code == 7
    assert "failed" in output.getvalue()
