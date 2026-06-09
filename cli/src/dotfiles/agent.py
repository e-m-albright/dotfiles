"""The canonical typed identifiers and per-vendor metadata for every AI tool we configure.

One source of truth: add a vendor here and the choices, headers, overview set, and
CLI-confirmation strings all follow. Nothing else should re-list the vendors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Agent = Literal["claude", "cursor", "codex", "gemini", "pi"]


@dataclass(frozen=True)
class Vendor:
    """An AI tool we deploy to, plus the facts that vary per vendor."""

    name: Agent
    display_name: str
    in_overview: bool  # tracked as a column in the agent-overview dashboard
    col: str = ""  # short matrix-column label; falls back to ``name`` when empty

    @property
    def column(self) -> str:
        """The label shown in matrix column headers (≤ the column width)."""
        return self.col or self.name


VENDORS: tuple[Vendor, ...] = (
    Vendor("claude", "Claude Code", in_overview=True),
    Vendor("cursor", "Cursor", in_overview=True),
    Vendor("codex", "Codex", in_overview=True),
    # The fifth slot is the ~/.gemini config dir — now driven by Antigravity CLI
    # (`agy`), not Gemini CLI (sunset 2026-06-18). The key stays "gemini" because
    # that's literally the config directory agy reads; the display is Antigravity.
    Vendor("gemini", "Antigravity", in_overview=True, col="agy"),
    Vendor("pi", "Pi", in_overview=True),
)

AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS)
# The vendors the agent-overview dashboard tracks. snapshot and skill-health
# both iterate exactly this set.
OVERVIEW_AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS if v.in_overview)
# name → short matrix-column label (e.g. gemini → "agy"). str-keyed to match the
# str-typed _AGENT_COLS the renderers iterate.
OVERVIEW_COLS: dict[str, str] = {v.name: v.column for v in VENDORS if v.in_overview}
