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


VENDORS: tuple[Vendor, ...] = (
    Vendor("claude", "Claude Code", in_overview=True),
    Vendor("cursor", "Cursor", in_overview=True),
    Vendor("codex", "Codex", in_overview=True),
    Vendor("gemini", "Gemini", in_overview=True),
    Vendor("pi", "Pi", in_overview=True),
)

AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS)
# The vendors the agent-overview dashboard tracks. snapshot and skill-health
# both iterate exactly this set.
OVERVIEW_AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS if v.in_overview)
