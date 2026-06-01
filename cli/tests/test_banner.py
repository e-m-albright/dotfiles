"""Brand banner rendering."""

from typer.testing import CliRunner

from dotfiles import __version__
from dotfiles.banner import BLOCK_LINES, gradient_banner
from dotfiles.cli.main import app
from tests.fakes import make_fake_context

runner = CliRunner()


def test_gradient_banner_preserves_glyphs_and_colors():
    banner = gradient_banner()
    rows = banner.plain.strip("\n").split("\n")
    assert rows[0] == BLOCK_LINES[0]
    assert len(rows) == len(BLOCK_LINES)
    # per-character color spans were applied
    assert len(banner.spans) > 0


def test_version_command_shows_banner_and_version():
    result = runner.invoke(app, ["version"], obj=make_fake_context())
    assert result.exit_code == 0
    assert __version__ in result.stdout
    assert "█" in result.stdout  # the wordmark rendered
