"""Brand banner: the DOTFILES wordmark with a horizontal gold gradient.

Presentation-only (adapter side). Built on rich.Text so it degrades gracefully on
non-truecolor terminals. Palette matches the TUI theme (#e8c34a).
"""

from __future__ import annotations

from collections.abc import Sequence

from rich.text import Text

# The "block" wordmark (single source of truth for the brand banner).
BLOCK_LINES: tuple[str, ...] = (
    "██████╗  ██████╗ ████████╗███████╗██╗██╗     ███████╗███████╗",
    "██╔══██╗██╔═══██╗╚══██╔══╝██╔════╝██║██║     ██╔════╝██╔════╝",
    "██║  ██║██║   ██║   ██║   █████╗  ██║██║     █████╗  ███████╗",
    "██║  ██║██║   ██║   ██║   ██╔══╝  ██║██║     ██╔══╝  ╚════██║",
    "██████╔╝╚██████╔╝   ██║   ██║     ██║███████╗███████╗███████║",
    "╚═════╝  ╚═════╝    ╚═╝   ╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝",
)

# pale gold -> theme gold -> dark goldenrod
_STOPS = ((255, 233, 168), (245, 215, 110), (232, 195, 74), (184, 134, 11))


def _grad(t: float) -> tuple[int, int, int]:
    t = min(max(t, 0.0), 0.999)
    seg = t * (len(_STOPS) - 1)
    i = int(seg)
    f = seg - i
    a, b = _STOPS[i], _STOPS[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))  # type: ignore[return-value]


def gradient_banner(lines: Sequence[str] = BLOCK_LINES) -> Text:
    """Build the wordmark as a rich.Text with a per-column horizontal gold gradient."""
    width = max((len(line) for line in lines), default=1)
    text = Text(no_wrap=True)
    for line in lines:
        for x, ch in enumerate(line):
            r, g, b = _grad(x / max(1, width - 1))
            text.append(ch, style=f"#{r:02x}{g:02x}{b:02x}")
        text.append("\n")
    return text
