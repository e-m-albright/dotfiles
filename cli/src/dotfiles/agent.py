"""The canonical typed registry for every AI tool we configure.

One source of truth: per (vendor, surface) the registry holds our **stance** —
``Deploy`` (we put something there globally, with the proof spec that verifies it
live), ``Native`` (the vendor ships it; nothing of ours to deploy), ``Local``
(supported only at a scope a global deploy can't reach), or ``None`` (nothing for
us there). Every view (overview, verify, instructions, doctor) derives from this
plus the capability matrix — nothing re-lists vendors, paths, or deploy intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Agent = Literal["claude", "cursor", "codex", "gemini", "pi", "hermes"]

# The agent surfaces we track per vendor. The first seven map 1:1 onto capability
# matrix rows (CAN); "settings" is plumbing (no capability claim).
SurfaceName = Literal[
    "rules",
    "skills",
    "subagents",
    "mcp",
    "hooks",
    "statusline",
    "permissions",
    "settings",
]

SURFACES: tuple[SurfaceName, ...] = (
    "rules",
    "skills",
    "subagents",
    "mcp",
    "hooks",
    "statusline",
    "permissions",
    "settings",
)

# How a Deploy stance is proven live (the HAVE probe semantics):
#   exists       — the path exists
#   md-dir       — a dir holding ≥1 *.md (subagents)
#   mdc-dir      — a dir holding ≥1 *.mdc (cursor rules)
#   skill-dirs   — a dir holding ≥1 skill subdir (counted)
#   contains     — a file whose text contains ``needle``
#   hook-intents — a config whose text wires every shared hook script (HOOK_INTENTS)
Proof = Literal["exists", "md-dir", "mdc-dir", "skill-dirs", "contains", "hook-intents"]


@dataclass(frozen=True)
class Deploy:
    """We deploy this surface globally: where it lands and how to prove it live."""

    path: str  # relative to ``root``
    proof: Proof = "exists"
    needle: str = ""  # for proof="contains"
    root: Literal["home", "repo"] = "home"


@dataclass(frozen=True)
class Native:
    """The vendor ships this surface out of the box — nothing of ours to deploy."""

    note: str


@dataclass(frozen=True)
class Local:
    """Supported, but only at a scope a global deploy can't reach (workspace/ext/beta)."""

    why: str


Stance = Deploy | Native | Local | None


@dataclass(frozen=True)
class Surfaces:
    """Our stance per agent surface for one vendor. ``None`` = nothing for us there."""

    rules: Stance = None
    skills: Stance = None
    subagents: Stance = None
    mcp: Stance = None
    hooks: Stance = None
    statusline: Stance = None
    permissions: Stance = None
    settings: Stance = None

    def stance(self, surface: SurfaceName) -> Stance:
        out: Stance = getattr(self, surface)
        return out


@dataclass(frozen=True)
class Vendor:
    """An AI tool we deploy to, plus the facts that vary per vendor."""

    name: Agent
    display_name: str
    in_overview: bool  # tracked as a column in the agent-overview dashboard
    surfaces: Surfaces
    col: str = ""  # short matrix-column label; falls back to ``name`` when empty

    @property
    def column(self) -> str:
        """The label shown in matrix column headers (≤ the column width)."""
        return self.col or self.name

    def deploy(self, surface: SurfaceName) -> Deploy | None:
        """The Deploy spec for *surface*, or None when our stance isn't a deploy."""
        stance = self.surfaces.stance(surface)
        return stance if isinstance(stance, Deploy) else None


# The uniform hook contract: each intent maps to the shared script every
# hook-capable vendor wires. A vendor's hooks deployment is proven by these
# basenames appearing in its LIVE hooks config (proof="hook-intents").
HOOK_INTENTS: tuple[tuple[str, str], ...] = (
    ("guard-file", "guard-sensitive-file.sh"),
    ("guard-shell", "guard-destructive-shell.sh"),
    ("format", "format-on-save.sh"),
    ("notify", "notify.sh"),
)


VENDORS: tuple[Vendor, ...] = (
    Vendor(
        "claude",
        "Claude Code",
        in_overview=True,
        surfaces=Surfaces(
            rules=Deploy(".claude/CLAUDE.md"),
            skills=Deploy(".claude/skills", proof="skill-dirs"),
            subagents=Deploy(".claude/agents", proof="md-dir"),
            mcp=Deploy(".claude.json"),
            hooks=Deploy(".claude/settings.json", proof="hook-intents"),
            statusline=Deploy(".claude/settings.json", proof="contains", needle="statusLine"),
            permissions=Deploy(".claude/settings.json", proof="contains", needle="permissions"),
            settings=Deploy(".claude/settings.json"),
        ),
    ),
    Vendor(
        "cursor",
        "Cursor",
        in_overview=True,
        surfaces=Surfaces(
            # Generated .mdc in-repo, loaded via the ~/.cursor/plugins/dotfiles symlink.
            rules=Deploy("ai/agents/cursor/rules", proof="mdc-dir", root="repo"),
            skills=Deploy(".cursor/skills", proof="skill-dirs"),
            # Cursor natively supports subagents (cursor.com/docs/subagents).
            subagents=Deploy(".cursor/agents", proof="md-dir"),
            mcp=Deploy(".cursor/mcp.json"),
            # Live hooks config rides the plugin symlink (cursor.com/docs/hooks).
            hooks=Deploy(".cursor/plugins/dotfiles/hooks/hooks.json", proof="hook-intents"),
            statusline=Local("statusline is beta — no stable global deploy surface"),
            permissions=Deploy(".cursor/cli-config.json", proof="contains", needle="permissions"),
            settings=Deploy(".cursor/cli-config.json"),
        ),
    ),
    Vendor(
        "codex",
        "Codex",
        in_overview=True,
        surfaces=Surfaces(
            rules=Deploy(".codex/AGENTS.md"),
            skills=Deploy(".agents/skills", proof="skill-dirs"),
            subagents=Deploy(".codex/agents", proof="md-dir"),
            mcp=Deploy(".codex/config.toml"),
            hooks=Deploy(".codex/hooks.json", proof="hook-intents"),
            statusline=Deploy(".codex/config.toml", proof="contains", needle="status_line"),
            permissions=Deploy(".codex/rules/default.rules"),
            settings=Deploy(".codex/config.toml"),
        ),
    ),
    Vendor(
        "gemini",
        "Antigravity",
        in_overview=True,
        col="agy",
        surfaces=Surfaces(
            rules=Deploy(".gemini/AGENTS.md"),
            skills=Deploy(".gemini/antigravity-cli/skills", proof="skill-dirs"),
            subagents=Local("workspace-local .agents/ agent-scripts only — no global dir"),
            mcp=Deploy(".gemini/settings.json"),
            hooks=Local("hook registration is workspace-local"),
            statusline=Native("Antigravity ships its own statusline"),
            permissions=Deploy(".gemini/settings.json", proof="contains", needle="exclude"),
            settings=Deploy(".gemini/settings.json"),
        ),
    ),
    Vendor(
        "pi",
        "Pi",
        in_overview=True,
        surfaces=Surfaces(
            rules=Deploy(".pi/agent/AGENTS.md"),
            skills=Deploy(".agents/skills", proof="skill-dirs"),
            subagents=Deploy(".pi/agent/agents", proof="md-dir"),
            mcp=None,  # proven absent (capability matrix: no)
            hooks=Deploy(".pi/agent/extensions/safe-git.ts"),
            statusline=Deploy(".pi/agent/extensions/git-status.ts"),
            permissions=Deploy(".pi/agent/permission-policy.json"),
            settings=Deploy(".pi/agent/settings.json"),
        ),
    ),
    Vendor(
        "hermes",
        "Hermes",
        in_overview=True,
        # Hermes (NousResearch hermes-agent) is a skills vendor for us. Everything
        # else it supports only at runtime / in Hermes-managed config we don't own.
        surfaces=Surfaces(
            rules=Local("loads project AGENTS.md at runtime; ~/.hermes/SOUL.md is Hermes' persona"),
            skills=Deploy(".hermes/skills", proof="skill-dirs"),
            subagents=Local("delegate_task is a runtime tool — no deploy dir"),
            mcp=Local("runtime MCP registry — no static config we own"),
            hooks=Local("~/.hermes/hooks schema undocumented — we don't deploy it"),
            statusline=None,  # TUI footer is fixed; no statusline surface found
            permissions=Local("tool policy lives in Hermes-managed config.yaml + sandbox"),
            settings=None,
        ),
    ),
)

AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS)
VENDOR_BY_NAME: dict[Agent, Vendor] = {v.name: v for v in VENDORS}


def surface_path(home: Path, vendor: Agent, surface: SurfaceName) -> Path:
    """Resolve a vendor's home-rooted Deploy path from the one registry.

    The single lookup every probe (doctor, overview, ...) should use instead of
    re-hardcoding ``~/.claude/settings.json`` and friends — so a path that moves
    in ``VENDORS`` propagates everywhere automatically. Raises ``KeyError`` when
    the vendor's stance for the surface isn't a home-rooted deploy (a wiring bug,
    surfaced loudly, not a silent miss).
    """
    deploy = VENDOR_BY_NAME[vendor].deploy(surface)
    if deploy is None or deploy.root != "home":
        raise KeyError(f"vendor {vendor!r} has no home-rooted {surface!r} deploy")
    return home / deploy.path


# The vendors the agent-overview dashboard tracks. snapshot and skill-health
# both iterate exactly this set.
OVERVIEW_AGENTS: tuple[Agent, ...] = tuple(v.name for v in VENDORS if v.in_overview)
# name → short matrix-column label (e.g. gemini → "agy"). str-keyed to match the
# str-typed _AGENT_COLS the renderers iterate.
OVERVIEW_COLS: dict[str, str] = {v.name: v.column for v in VENDORS if v.in_overview}
