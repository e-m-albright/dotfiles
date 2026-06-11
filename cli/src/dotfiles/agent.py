"""The canonical typed identifiers and per-vendor metadata for every AI tool we configure.

One source of truth: add a vendor here and the choices, headers, overview set, and
CLI-confirmation strings all follow. Nothing else should re-list the vendors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Agent = Literal["claude", "cursor", "codex", "gemini", "pi", "hermes"]


@dataclass(frozen=True)
class VendorPaths:
    """Home-relative paths for this vendor's agent surfaces. ``None`` = n/a (skipped)."""

    skills: str | None = None
    subagents: str | None = None  # the subagent .md dir — one path for deploy + verify
    rules: str | None = None
    mcp: str | None = None
    hooks: str | None = None
    instructions: str | None = None
    settings: str | None = None

    def resolve(self, home: Path, rel: str | None) -> Path | None:
        return None if rel is None else home / rel

    def exists(self, home: Path, rel: str | None) -> bool:
        path = self.resolve(home, rel)
        return path.exists() if path is not None else False


@dataclass(frozen=True)
class Vendor:
    """An AI tool we deploy to, plus the facts that vary per vendor."""

    name: Agent
    display_name: str
    in_overview: bool  # tracked as a column in the agent-overview dashboard
    paths: VendorPaths
    col: str = ""  # short matrix-column label; falls back to ``name`` when empty

    @property
    def column(self) -> str:
        """The label shown in matrix column headers (≤ the column width)."""
        return self.col or self.name


VENDORS: tuple[Vendor, ...] = (
    Vendor(
        "claude",
        "Claude Code",
        in_overview=True,
        paths=VendorPaths(
            skills=".claude/skills",
            subagents=".claude/agents",
            rules=".claude/rules",
            mcp=".claude.json",
            hooks=".claude/settings.json",
            instructions=".claude/CLAUDE.md",
            settings=".claude/settings.json",
        ),
    ),
    Vendor(
        "cursor",
        "Cursor",
        in_overview=True,
        paths=VendorPaths(
            skills=".cursor/skills",
            # Cursor natively supports subagents (cursor.com/docs/subagents).
            subagents=".cursor/agents",
            mcp=".cursor/mcp.json",
            # Cursor hooks live inside cli-config.json (cursor.com/docs/hooks).
            hooks=".cursor/cli-config.json",
            settings=".cursor/cli-config.json",
        ),
    ),
    Vendor(
        "codex",
        "Codex",
        in_overview=True,
        paths=VendorPaths(
            skills=".agents/skills",
            subagents=".codex/agents",
            mcp=".codex/config.toml",
            hooks=".codex/hooks.json",
            instructions=".codex/AGENTS.md",
            settings=".codex/config.toml",
        ),
    ),
    Vendor(
        "gemini",
        "Antigravity",
        in_overview=True,
        col="agy",
        paths=VendorPaths(
            skills=".gemini/antigravity-cli/skills",
            mcp=".gemini/settings.json",
            instructions=".gemini/AGENTS.md",
            settings=".gemini/settings.json",
        ),
    ),
    Vendor(
        "pi",
        "Pi",
        in_overview=True,
        paths=VendorPaths(
            skills=".agents/skills",
            subagents=".pi/agent/agents",
            instructions=".pi/agent/AGENTS.md",
            settings=".pi/agent/settings.json",
        ),
    ),
    Vendor(
        "hermes",
        "Hermes",
        in_overview=True,
        # Hermes (NousResearch hermes-agent) is a skills vendor for us. It loads
        # behavioural rules from project AGENTS.md/CLAUDE.md (auto-injected from the
        # CWD) — there is no global rules slot we own: ~/.hermes/SOUL.md is Hermes'
        # own seeded persona, not ours to overwrite, and ~/.hermes/config.yaml is
        # Hermes-managed (model/provider/keys). So: skills only.
        paths=VendorPaths(
            skills=".hermes/skills",
        ),
    ),
)

AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS)
VENDOR_BY_NAME: dict[Agent, Vendor] = {v.name: v for v in VENDORS}


def surface_path(home: Path, vendor: Agent, surface: str) -> Path:
    """Resolve a vendor's home-relative surface path from the one registry.

    The single lookup every probe (doctor, overview, ...) should use instead of
    re-hardcoding ``~/.claude/settings.json`` and friends — so a path that moves
    in ``VENDORS`` propagates everywhere automatically. Raises ``KeyError`` when
    the vendor declares no such surface (a wiring bug, surfaced loudly, not a
    silent miss).
    """
    rel: str | None = getattr(VENDOR_BY_NAME[vendor].paths, surface)
    if rel is None:
        raise KeyError(f"vendor {vendor!r} has no {surface!r} surface")
    return home / rel


# The vendors the agent-overview dashboard tracks. snapshot and skill-health
# both iterate exactly this set.
OVERVIEW_AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS if v.in_overview)
# name → short matrix-column label (e.g. gemini → "agy"). str-keyed to match the
# str-typed _AGENT_COLS the renderers iterate.
OVERVIEW_COLS: dict[str, str] = {v.name: v.column for v in VENDORS if v.in_overview}

# attribute → per-vendor home-relative path (None = n/a). Built from VENDORS.
SURFACE_PATHS: dict[str, dict[Agent, str | None]] = {
    attr: {v.name: getattr(v.paths, attr) for v in VENDORS}
    for attr in (
        "skills",
        "subagents",
        "rules",
        "mcp",
        "hooks",
        "instructions",
        "settings",
    )
}
