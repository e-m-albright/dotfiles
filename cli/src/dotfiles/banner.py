"""DOTFILES wordmark with the horizontal Red Granite gradient."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from rich.console import Console
from rich.text import Text

BLOCK_LINES: tuple[str, ...] = (
    "██████╗  ██████╗ ████████╗███████╗██╗██╗     ███████╗███████╗",
    "██╔══██╗██╔═══██╗╚══██╔══╝██╔════╝██║██║     ██╔════╝██╔════╝",
    "██║  ██║██║   ██║   ██║   █████╗  ██║██║     █████╗  ███████╗",
    "██║  ██║██║   ██║   ██║   ██╔══╝  ██║██║     ██╔══╝  ╚════██║",
    "██████╔╝╚██████╔╝   ██║   ██║     ██║███████╗███████╗███████║",
    "╚═════╝  ╚═════╝    ╚═╝   ╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝",
)

# Feldspar and iron through quartz, black mica, and mineral gray.
_STOPS = (
    (228, 210, 189),
    (194, 154, 130),
    (166, 103, 87),
    (123, 80, 73),
    (81, 75, 73),
    (48, 56, 58),
)


def _gradient(position: float) -> tuple[int, int, int]:
    position = min(max(position, 0.0), 0.999)
    segment = position * (len(_STOPS) - 1)
    index = int(segment)
    fraction = segment - index
    start, end = _STOPS[index], _STOPS[index + 1]

    def mix(channel: int) -> int:
        return round(start[channel] + (end[channel] - start[channel]) * fraction)

    return (mix(0), mix(1), mix(2))


def gradient_banner(lines: Sequence[str] = BLOCK_LINES) -> Text:
    """Build the wordmark with a per-column horizontal gradient."""
    width = max((len(line) for line in lines), default=1)
    text = Text(no_wrap=True)
    for line in lines:
        for column, character in enumerate(line):
            red, green, blue = _gradient(1 - column / max(1, width - 1))
            text.append(character, style=f"#{red:02x}{green:02x}{blue:02x}")
        text.append("\n")
    return text


def print_banner(*, stderr: bool = False) -> None:
    """Print the banner, using color only on terminals that permit it."""
    stream = sys.stderr if stderr else sys.stdout
    Console(
        file=stream,
        color_system="truecolor" if stream.isatty() else None,
        no_color=os.environ.get("NO_COLOR") is not None,
    ).print(gradient_banner())
