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
    in_overview: bool  # tracked by the agent-overview dashboard (its rows carry no `pi`)
    cli_confirmation: str  # how to confirm the deploy from that tool's own CLI/GUI


VENDORS: tuple[Vendor, ...] = (
    Vendor(
        "claude",
        "Claude Code",
        in_overview=True,
        cli_confirmation=(
            "CLI confirmation: skills auto-listed in every Claude Code session via Skill tool"
        ),
    ),
    Vendor(
        "cursor",
        "Cursor",
        in_overview=True,
        cli_confirmation="CLI confirmation: GUI only — Cursor → Settings → MCP / Rules",
    ),
    Vendor(
        "codex",
        "Codex",
        in_overview=True,
        cli_confirmation="CLI confirmation: 'codex' (interactive) — no list-skills subcommand",
    ),
    Vendor(
        "gemini",
        "Gemini",
        in_overview=True,
        cli_confirmation="CLI confirmation: 'gemini' (interactive)",
    ),
    Vendor(
        "pi",
        "Pi",
        in_overview=False,
        cli_confirmation="CLI confirmation: 'pi' (interactive, LM Studio local-first)",
    ),
)

AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS)
# The vendors the agent-overview dashboard tracks. snapshot and skill-health
# both iterate exactly this set.
OVERVIEW_AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS if v.in_overview)
