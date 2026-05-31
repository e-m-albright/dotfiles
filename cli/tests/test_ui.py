from io import StringIO

from rich.console import Console

from dotfiles_cli.cli.ui import render_steps
from dotfiles_cli.core.models import StepResult


def test_render_steps_writes_each_message_with_a_glyph() -> None:
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=100)
    render_steps(
        console,
        [
            StepResult(level="success", message="ready"),
            StepResult(level="warn", message="careful"),
            StepResult(level="error", message="boom"),
            StepResult(level="info", message="noted"),
        ],
    )
    out = buf.getvalue()
    assert "ready" in out
    assert "careful" in out
    assert "boom" in out
    assert "noted" in out
    # success/warn/error use distinct leading glyphs
    assert "✓" in out
    assert "⚠" in out
    assert "✗" in out
