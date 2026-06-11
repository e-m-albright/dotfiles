"""`dotfiles agent instructions`: the harness manifest.

What context an agent is actually fed, split by **load mode** — paid every session
vs reachable only when pulled — with an estimated token cost per source. Answers a
different question than its siblings:

- ``agent overview``   — what's deployed to which vendor (deployment state).
- ``agent catechism``  — which code-health rite to reach for (doctrine routing).
- ``agent instructions`` (here) — the *context budget*: what every session pays for
  by default, what's reachable on demand, the behavior-shaping harness config, and
  the engineering map it all hangs off.

Canonical sources only (under the repo), so the manifest is deterministic and
testable without probing a deployed machine.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, RootModel

from dotfiles.cmd.agent.catechism import DOCTRINE


def est_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — a budget gauge, not an exact count."""
    return len(text) // 4


class LoadMode(StrEnum):
    """How a source reaches the model."""

    default = "default"  # in every session's context — the budget you always pay
    reachable = "reachable"  # pulled on demand (trigger, link, or dispatch)
    harness = "harness"  # shapes behavior, not context text (hooks, permissions, MCP)


class ContextItem(BaseModel):
    """One source the harness provides, classified by how it reaches the model."""

    model_config = ConfigDict(frozen=True)

    name: str
    source: str  # repo-relative path or glob
    mode: LoadMode
    est_tokens: int  # estimated context cost; 0 for non-text harness config
    count: int  # number of files this item spans
    note: str


class MapColumn(BaseModel):
    """One column of the engineering map: a band of stable IDs and its source doc."""

    model_config = ConfigDict(frozen=True)

    name: str
    ids: str
    source: str


class InstructionsManifest(BaseModel):
    """The full harness manifest: every context source + the engineering map."""

    model_config = ConfigDict(frozen=True)

    items: tuple[ContextItem, ...]
    columns: tuple[MapColumn, ...]

    def tokens_for(self, mode: LoadMode) -> int:
        return sum(i.est_tokens for i in self.items if i.mode is mode)

    def items_for(self, mode: LoadMode) -> list[ContextItem]:
        return [i for i in self.items if i.mode is mode]


_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_NUMBERED_HEADER = re.compile(r"^#{2,3} \d+\. ", re.MULTILINE)


def _read(path: Path) -> str:
    """File text, or '' if absent/unreadable (the manifest degrades, never crashes)."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter, body) for a SKILL.md — frontmatter is the always-loaded index."""
    match = _FRONTMATTER.match(text)
    if not match:
        return "", text
    return match.group(0), text[match.end() :]


def _file_item(root: Path, rel: str, name: str, mode: LoadMode, note: str) -> ContextItem:
    text = _read(root / rel)
    return ContextItem(
        name=name,
        source=rel,
        mode=mode,
        est_tokens=est_tokens(text),
        count=1 if text else 0,
        note=note,
    )


def _skill_items(root: Path) -> tuple[ContextItem, ContextItem]:
    """Skills split: frontmatter index (default) vs bodies (reachable on trigger)."""
    files = sorted((root / "ai" / "skills").glob("*/SKILL.md"))
    index_tokens = body_tokens = 0
    for skill in files:
        frontmatter, body = _split_frontmatter(_read(skill))
        index_tokens += est_tokens(frontmatter)
        body_tokens += est_tokens(body)
    index = ContextItem(
        name="skill index",
        source="ai/skills/*/SKILL.md",
        mode=LoadMode.default,
        est_tokens=index_tokens,
        count=len(files),
        note="frontmatter (name + description) only; bodies load on trigger",
    )
    bodies = ContextItem(
        name="skill bodies",
        source="ai/skills/*/SKILL.md",
        mode=LoadMode.reachable,
        est_tokens=body_tokens,
        count=len(files),
        note="full instructions, loaded only when a trigger fires",
    )
    return index, bodies


def _docs_item(root: Path) -> ContextItem:
    """The engineering map + its deep-dives (the DOCTRINE backbone) — reachable on link."""
    tokens = count = 0
    for layer in DOCTRINE:
        text = _read(root / layer.doc)
        if text:
            count += 1
            tokens += est_tokens(text)
    return ContextItem(
        name="reference docs",
        source="ENGINEERING.md + docs/…",
        mode=LoadMode.reachable,
        est_tokens=tokens,
        count=count,
        note="the engineering map + deep-dives; loaded when linked or read",
    )


def _subagents_item(root: Path) -> ContextItem:
    files = sorted((root / "ai" / "subagents").glob("*.md"))
    tokens = sum(est_tokens(_read(f)) for f in files)
    return ContextItem(
        name="subagents",
        source="ai/subagents/*.md",
        mode=LoadMode.reachable,
        est_tokens=tokens,
        count=len(files),
        note="dispatched via the Agent tool; never in main context",
    )


class _McpServersFile(RootModel[dict[str, object]]):
    """mcp-servers.json: a flat map of server name → config (typed for the count)."""


def _mcp_count(root: Path) -> int:
    """Active MCP servers — a flat name→config map; `_disabled`/`$comment` keys skipped."""
    raw = _read(root / "ai" / "agents" / "shared" / "mcp-servers.json")
    if not raw:
        return 0
    try:
        servers = _McpServersFile.model_validate_json(raw).root
    except ValueError:
        return 0
    return sum(1 for key in servers if not key.startswith(("_", "$")))


def _harness_items(root: Path) -> list[ContextItem]:
    """Behavior-shaping config: guards, deny-vocab, permissions, MCP. Not context text."""
    hooks = sorted((root / "ai" / "agents" / "shared" / "hooks").glob("*.sh"))
    deny = _read(root / "ai" / "agents" / "shared" / "deny-commands.yaml")
    return [
        ContextItem(
            name="guard hooks",
            source="ai/agents/shared/hooks/*.sh",
            mode=LoadMode.harness,
            est_tokens=0,
            count=len(hooks),
            note="pre-tool guards (destructive-shell, sensitive-file)",
        ),
        ContextItem(
            name="deny vocabulary",
            source="ai/agents/shared/deny-commands.yaml",
            mode=LoadMode.harness,
            est_tokens=0,
            count=1 if deny else 0,
            note="commands refused outright, one source translated per vendor (G11)",
        ),
        ContextItem(
            name="permission profile",
            source="ai/.agents/safe-commands.yaml",
            mode=LoadMode.harness,
            est_tokens=0,
            count=1 if _read(root / "ai" / ".agents" / "safe-commands.yaml") else 0,
            note="auto-allowed safe-command tiers",
        ),
        ContextItem(
            name="mcp servers",
            source="ai/agents/shared/mcp-servers.json",
            mode=LoadMode.harness,
            est_tokens=0,
            count=_mcp_count(root),
            note="external tool servers wired into the harness",
        ),
    ]


def _map_columns(root: Path) -> tuple[MapColumn, ...]:
    """The four columns of the engineering map, with live counts where derivable."""
    principles = len(_NUMBERED_HEADER.findall(_read(root / "docs" / "engineering-philosophy.md")))
    gates = len(
        _NUMBERED_HEADER.findall(_read(root / "docs" / "knowledge" / "engineering-gates.md"))
    )
    skills = len(sorted((root / "ai" / "skills").glob("*/SKILL.md")))
    return (
        MapColumn(
            name="Doctrine",
            ids=f"K1-K8 · P1-P{principles or 12}",
            source="rules.md · engineering-philosophy.md",
        ),
        MapColumn(
            name="Enforcement",
            ids=f"G1-G{gates or 14}",
            source="engineering-gates.md",
        ),
        MapColumn(name="Defense in depth", ids="L0-L5", source="how-we-build.md"),
        MapColumn(
            name="Tools",
            ids=f"{skills} lenses/skills",
            source="code-health-portfolio.md",
        ),
    )


def build_manifest(dotfiles_dir: Path) -> InstructionsManifest:
    """Assemble the harness manifest from the repo's canonical sources."""
    index, bodies = _skill_items(dotfiles_dir)
    items: tuple[ContextItem, ...] = (
        _file_item(
            dotfiles_dir,
            "ai/agents/shared/rules.md",
            "kernel",
            LoadMode.default,
            "the universal agent kernel, deployed verbatim to every vendor · K1-K8",
        ),
        _file_item(
            dotfiles_dir,
            "AGENTS.md",
            "project",
            LoadMode.default,
            "CLAUDE.md/GEMINI.md symlink to this; always loaded per project",
        ),
        index,
        bodies,
        _docs_item(dotfiles_dir),
        _subagents_item(dotfiles_dir),
        *_harness_items(dotfiles_dir),
    )
    return InstructionsManifest(items=items, columns=_map_columns(dotfiles_dir))
