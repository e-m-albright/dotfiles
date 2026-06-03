"""Best-effort peek at what's *running* inside a zellij session.

zellij doesn't expose typed shell history, but it serializes per-session pane
state to a `session_info` cache (for its own session-manager / resurrection).
We read the terminal-pane titles from there so the TUI can preview "what's going
on" in each session (e.g. ``Claude Code · nvim``).

This reads zellij's *undocumented* cache format at an OS-specific path, so every
step degrades silently to ``[]`` — a format/path change must never break the
deck, only drop the preview line. ``home``/``platform`` are injected for tests.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Pane blocks in session-metadata.kdl carry these one-per-line fields.
_PLUGIN = re.compile(r"\bis_plugin\s+true\b")
_SUPPRESSED = re.compile(r"\bis_suppressed\s+true\b")
_EXITED = re.compile(r"\bexited\s+true\b")
_TITLE = re.compile(r'\btitle\s+"([^"]*)"')


def zellij_cache_root(home: Path, platform: str) -> Path:
    """Where zellij keeps its caches for this OS (not guaranteed to exist)."""
    if platform == "darwin":
        return home / "Library" / "Caches" / "org.Zellij-Contributors.Zellij"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else home / ".cache"
    return base / "zellij"


def _balanced(text: str, brace_at: int) -> str:
    """Inner text of the ``{...}`` block whose opening brace is at *brace_at*."""
    depth = 0
    for i in range(brace_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_at + 1 : i]
    return text[brace_at + 1 :]


def _section(text: str, name: str) -> str | None:
    """The inner text of a top-level ``name { ... }`` block, or None."""
    m = re.search(rf"\b{name}\s*\{{", text)
    return _balanced(text, m.end() - 1) if m else None


def parse_pane_titles(metadata: str) -> list[str]:
    """Titles of the real (non-plugin, non-suppressed, live) terminal panes.

    Plugin panes are zellij's own tab-bar/status-bar chrome; suppressed/exited
    panes aren't what you'd call "running", so all three are filtered out.
    """
    panes = _section(metadata, "panes")
    if panes is None:
        return []
    titles: list[str] = []
    for m in re.finditer(r"\bpane\s*\{", panes):
        block = _balanced(panes, m.end() - 1)
        if _PLUGIN.search(block) or _SUPPRESSED.search(block) or _EXITED.search(block):
            continue
        title = _TITLE.search(block)
        if title and title.group(1).strip():
            titles.append(title.group(1).strip())
    return titles


def session_program_titles(*, cache_root: Path, name: str) -> list[str]:
    """Running terminal-pane titles for session *name*, or [] on any failure."""
    try:
        files = sorted(cache_root.glob(f"*/session_info/{name}/session-metadata.kdl"))
    except OSError:
        return []
    if not files:
        return []
    try:
        metadata = files[-1].read_text()
    except OSError:
        return []
    return parse_pane_titles(metadata)
