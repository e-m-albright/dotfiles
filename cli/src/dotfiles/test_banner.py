"""Brand banner rendering."""

from io import StringIO

from rich.console import Console

from dotfiles.banner import (
    _STOPS,
    BLOCK_LINES,
    COMPACT_LINES,
    gradient_banner,
    print_banner,
)


def test_compact_banner_matches_lines():
    rows = gradient_banner(COMPACT_LINES).plain.strip("\n").split("\n")
    assert rows == list(COMPACT_LINES)


def test_print_banner_emits_glyphs():
    buf = StringIO()
    print_banner(console=Console(file=buf, force_terminal=True, width=80))
    assert "█" in buf.getvalue()


def test_gradient_banner_preserves_glyphs_and_colors():
    banner = gradient_banner()
    rows = banner.plain.strip("\n").split("\n")
    assert rows[0] == BLOCK_LINES[0]
    assert len(rows) == len(BLOCK_LINES)
    # per-character color spans were applied
    assert len(banner.spans) > 0
    assert _STOPS[0] == (255, 240, 179)
    assert _STOPS[-1] == (184, 107, 0)
