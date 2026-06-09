"""The cross-vendor capability matrix: what each of the 5 agents supports.

The machine-readable source of the vendor x capability table in
docs/knowledge/agent-fleet.md (the prose doc mirrors this; a drift test holds
them in sync). Printed inside ``dotfiles agent overview``.

Two layers:
- **Intent** (this module's data) — the *target state* per (capability, vendor),
  hand-authored to match agent-fleet.md: required / canonical (the Pi end-state
  we converge toward) / different-mechanism / n-a.
- **Liveness** (the service) — a verifiable probe of what's actually deployed,
  so a target that isn't met shows as a gap (✗), never a false green. This is
  the "single live truth, reconciled to the doc" the fleet work is built on.

The ``front_runner`` field records who pioneered each capability — the landscape
dimension: Claude Code tends to ship first, the others copy, and Pi is where we
want to own the end state. It feeds the feature-map / Pi-decision work.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import AGENTS, Agent
from dotfiles.cmd.agent.config import (
    ClaudeSettingsProbe,
    GeminiSettings,
    InstalledPlugins,
    McpServersFile,
    SettingsWithPermissions,
    load_config,
)


def _read_text(path: Path) -> str:
    """The file's text, or '' if it's absent or unreadable."""
    try:
        return path.read_text()
    except OSError:
        return ""


def _has_subdir(path: Path) -> bool:
    """True if *path* is a directory holding at least one subdirectory."""
    return path.is_dir() and any(child.is_dir() for child in path.iterdir())


def _has_file_with_suffix(path: Path, suffix: str) -> bool:
    """True if *path* is a directory holding at least one file with *suffix*."""
    return path.is_dir() and any(
        child.is_file() and child.suffix == suffix for child in path.iterdir()
    )


# The doc the matrix mirrors; we warn when its "Last reviewed" stamp goes stale.
FLEET_DOC_REL = ("docs", "knowledge", "agent-fleet.md")
FLEET_STALE_DAYS = 90
_REVIEWED_RE = re.compile(r"Last reviewed\D*(\d{4})-(\d{2})-(\d{2})")


def fleet_doc_reviewed(dotfiles_dir: Path) -> date | None:
    """The 'Last reviewed' date stamped in agent-fleet.md, or None if absent."""
    match = _REVIEWED_RE.search(_read_text(dotfiles_dir.joinpath(*FLEET_DOC_REL)))
    if match is None:
        return None
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def fleet_doc_stale_days(dotfiles_dir: Path, today: date) -> int | None:
    """Days since agent-fleet.md was last reviewed, or None if unstamped."""
    reviewed = fleet_doc_reviewed(dotfiles_dir)
    return None if reviewed is None else (today - reviewed).days


# Target intent of a (capability, vendor) cell, mirroring agent-fleet.md.
CellIntent = Literal["required", "canonical", "different", "na"]


class Capability(BaseModel):
    """One capability row: who pioneered it + the target intent per vendor."""

    model_config = ConfigDict(frozen=True)

    key: str
    front_runner: str  # who shipped it first ("" = universal / no clear pioneer)
    intents: dict[Agent, CellIntent]


def _cap(
    key: str,
    front_runner: str,
    claude: CellIntent,
    cursor: CellIntent,
    codex: CellIntent,
    gemini: CellIntent,
    pi: CellIntent,
) -> Capability:
    """Terse constructor so the matrix reads like the doc table it mirrors."""
    return Capability(
        key=key,
        front_runner=front_runner,
        intents={"claude": claude, "cursor": cursor, "codex": codex, "gemini": gemini, "pi": pi},
    )


# Mirrors the "Capability matrix (target state)" table in agent-fleet.md, row for
# row. Grouped: context surfaces, integration, UX/safety, extensibility.
#                  key            fr        claude     cursor     codex        gemini     pi
CAPABILITY_MATRIX: tuple[Capability, ...] = (
    _cap("rules", "", "required", "required", "required", "required", "required"),
    _cap("skills", "claude", "required", "required", "required", "na", "required"),
    _cap("subagents", "claude", "required", "na", "required", "na", "required"),
    _cap("mcp", "claude", "required", "required", "required", "required", "na"),
    _cap("hooks", "claude", "required", "required", "required", "na", "na"),
    _cap("statusline", "claude", "required", "na", "required", "na", "canonical"),
    _cap("permissions", "claude", "required", "required", "different", "required", "required"),
    _cap("plugins", "claude", "required", "na", "na", "na", "na"),
)


class CapabilityCell(BaseModel):
    """One rendered cell: the target intent and whether it's live-deployed."""

    model_config = ConfigDict(frozen=True)

    intent: CellIntent
    present: bool


class CapabilityRow(BaseModel):
    """One capability across all vendors, with live probe results per cell."""

    model_config = ConfigDict(frozen=True)

    capability: str
    front_runner: str
    cells: dict[str, CapabilityCell]


class CapabilityMatrixService:
    """Compose the target-intent matrix with live deployment probes."""

    def __init__(self, *, home: Path, dotfiles_dir: Path) -> None:
        self._home = home
        self._dotfiles = dotfiles_dir

    def rows(self) -> list[CapabilityRow]:
        """One CapabilityRow per capability, intents + live probes filled in."""
        rows: list[CapabilityRow] = []
        for cap in CAPABILITY_MATRIX:
            cells = {
                agent: CapabilityCell(
                    intent=cap.intents[agent],
                    # n/a cells are never probed — they're absent by design.
                    present=cap.intents[agent] != "na" and self._probe(cap.key, agent),
                )
                for agent in AGENTS
            }
            rows.append(
                CapabilityRow(capability=cap.key, front_runner=cap.front_runner, cells=cells)
            )
        return rows

    # ------------------------------------------------------------------
    # Liveness probes — each returns True iff the capability is deployed.
    # ------------------------------------------------------------------

    def _probe(self, capability: str, agent: Agent) -> bool:
        probes: dict[str, Callable[[Agent], bool]] = {
            "rules": self._has_rules,
            "skills": self._has_skills,
            "subagents": self._has_subagents,
            "mcp": self._has_mcp,
            "hooks": self._has_hooks,
            "statusline": self._has_statusline,
            "permissions": self._has_permissions,
            "plugins": self._has_plugins,
        }
        probe = probes.get(capability)
        return probe(agent) if probe is not None else False

    def _has_skills(self, agent: Agent) -> bool:
        h = self._home
        dirs: dict[Agent, Path] = {
            "claude": h / ".claude" / "skills",
            "cursor": h / ".cursor" / "skills-cursor",
            "codex": h / ".agents" / "skills",  # codex + pi read the shared dir
            "pi": h / ".agents" / "skills",
        }
        path = dirs.get(agent)
        return path is not None and _has_subdir(path)

    def _has_subagents(self, agent: Agent) -> bool:
        h = self._home
        dirs: dict[Agent, Path] = {
            "claude": h / ".claude" / "agents",
            "codex": h / ".codex" / "agents",
            "pi": h / ".pi" / "agent" / "agents",
        }
        path = dirs.get(agent)
        return path is not None and _has_file_with_suffix(path, ".md")

    def _has_plugins(self, agent: Agent) -> bool:
        # Only Claude ships a managed plugin marketplace (others: n/a).
        if agent != "claude":
            return False
        cfg = load_config(
            self._home / ".claude" / "plugins" / "installed_plugins.json", InstalledPlugins
        )
        return cfg is not None and bool(cfg.plugins)

    def _has_rules(self, agent: Agent) -> bool:
        h, d = self._home, self._dotfiles
        paths: dict[Agent, Path] = {
            "claude": h / ".claude" / "CLAUDE.md",
            "codex": h / ".codex" / "AGENTS.md",
            "gemini": h / ".gemini" / "GEMINI.md",
            "pi": h / ".pi" / "agent" / "AGENTS.md",
            "cursor": d / "ai" / "agents" / "cursor" / "rules" / "shared-rules.mdc",
        }
        path = paths.get(agent)
        return path is not None and path.exists()

    def _has_mcp(self, agent: Agent) -> bool:
        h = self._home
        if agent == "codex":
            return "[mcp_servers" in _read_text(h / ".codex" / "config.toml")
        json_paths: dict[Agent, Path] = {
            "claude": h / ".claude.json",
            "cursor": h / ".cursor" / "mcp.json",
            "gemini": h / ".gemini" / "settings.json",
        }
        path = json_paths.get(agent)
        if path is None:
            return False
        cfg = load_config(path, McpServersFile)
        return cfg is not None and bool(cfg.mcp_servers)

    def _has_statusline(self, agent: Agent) -> bool:
        h = self._home
        if agent == "claude":
            cfg = load_config(h / ".claude" / "settings.json", ClaudeSettingsProbe)
            return cfg is not None and cfg.status_line is not None
        if agent == "codex":
            return "[tui]" in _read_text(h / ".codex" / "config.toml")
        if agent == "pi":
            return (h / ".pi" / "agent" / "extensions" / "git-status.ts").exists()
        return False

    def _has_permissions(self, agent: Agent) -> bool:
        h = self._home
        if agent == "claude":
            cfg = load_config(h / ".claude" / "settings.json", ClaudeSettingsProbe)
            return cfg is not None and bool(cfg.permissions.deny or cfg.permissions.allow)
        if agent == "cursor":
            cur = load_config(h / ".cursor" / "cli-config.json", SettingsWithPermissions)
            return cur is not None and bool(cur.permissions.deny or cur.permissions.allow)
        if agent == "codex":
            return (h / ".codex" / "rules" / "default.rules").exists()
        if agent == "gemini":
            gem = load_config(h / ".gemini" / "settings.json", GeminiSettings)
            return gem is not None and gem.tools.exclude is not None
        if agent == "pi":
            return (h / ".pi" / "agent" / "permission-policy.json").exists()
        return False

    def _has_hooks(self, agent: Agent) -> bool:
        h, d = self._home, self._dotfiles
        if agent == "claude":
            cfg = load_config(h / ".claude" / "settings.json", ClaudeSettingsProbe)
            return cfg is not None and bool(cfg.hooks)
        if agent == "codex":
            return (h / ".codex" / "hooks.json").exists()
        if agent == "cursor":
            # Cursor hooks ship through its plugin, which references the repo
            # source rather than a copied home file.
            return (d / "ai" / "agents" / "cursor" / "hooks" / "hooks.json").exists()
        return False
