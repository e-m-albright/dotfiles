"""Brand banner rendering."""

from dotfiles.banner import _STOPS, BLOCK_LINES, gradient_banner


def test_gradient_banner_preserves_wordmark_and_colors() -> None:
    banner = gradient_banner()
    assert banner.plain.rstrip().splitlines() == list(BLOCK_LINES)
    assert banner.spans
    assert str(banner.spans[0].style) == "#30383a"
    assert _STOPS[0] == (228, 210, 189)
    assert _STOPS[-1] == (48, 56, 58)
