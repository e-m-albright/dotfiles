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

from dotfiles.agent import VENDORS
from dotfiles.cmd.agent.catechism import CATECHISM, DOCTRINE, CatechismEntry, DoctrineLayer


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
    vendor_gaps: tuple[str, ...] = ()  # vendor columns that don't get this surface


class MapColumn(BaseModel):
    """One column of the engineering map: a band of stable IDs and its source doc."""

    model_config = ConfigDict(frozen=True)

    name: str
    ids: str
    source: str


class ToolItem(BaseModel):
    """One tool in the agent's surface — what it can DO, and whether it mutates state."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: str  # file · search · exec · web · agent · meta · mcp
    mutating: bool  # changes state? (the mutating ones are what the guardrails gate)
    note: str


class HarnessLayer(BaseModel):
    """One layer of the five-layer harness model, mapped to what this repo provides."""

    model_config = ConfigDict(frozen=True)

    name: str
    pieces: str  # the concrete things in this repo that fill the layer
    note: str


class InstructionsManifest(BaseModel):
    """The full harness manifest: context sources, the map, the tool surface, layers."""

    model_config = ConfigDict(frozen=True)

    items: tuple[ContextItem, ...]
    columns: tuple[MapColumn, ...]
    tools: tuple[ToolItem, ...]
    layers: tuple[HarnessLayer, ...]
    doctrine: tuple[DoctrineLayer, ...]  # the map's backbone (subsumes catechism)
    routing: tuple[CatechismEntry, ...]  # symptom → rite (subsumes catechism)

    def tokens_for(self, mode: LoadMode) -> int:
        return sum(i.est_tokens for i in self.items if i.mode is mode)

    def items_for(self, mode: LoadMode) -> list[ContextItem]:
        return [i for i in self.items if i.mode is mode]


def _vendor_gaps(surface: str) -> tuple[str, ...]:
    """Vendor column labels that have no path for *surface* — the ones it skips."""
    return tuple(v.column for v in VENDORS if getattr(v.paths, surface) is None)


_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_NUMBERED_HEADER = re.compile(r"^#{2,3} \d+\. ", re.MULTILINE)

# The agent's built-in tool surface (Claude Code). A reference constant — these are
# harness-provided, not repo files — annotated by whether they mutate state, because
# the mutating ones are exactly what the guardrails (guard hooks) sit in front of.
_BUILTIN_TOOLS: tuple[ToolItem, ...] = (
    ToolItem(name="Read", kind="file", mutating=False, note="files, PDFs, images, notebooks"),
    ToolItem(name="Glob", kind="search", mutating=False, note="find files by name/pattern"),
    ToolItem(name="Grep", kind="search", mutating=False, note="search file contents (ripgrep)"),
    ToolItem(
        name="Edit",
        kind="file",
        mutating=True,
        note="exact string replace · guarded: sensitive-file",
    ),
    ToolItem(
        name="Write", kind="file", mutating=True, note="create/overwrite · guarded: sensitive-file"
    ),
    ToolItem(
        name="Bash",
        kind="exec",
        mutating=True,
        note="shell · guarded: destructive-shell + deny-vocab",
    ),
    ToolItem(name="WebFetch", kind="web", mutating=False, note="fetch + read a URL (grounding)"),
    ToolItem(name="WebSearch", kind="web", mutating=False, note="search the web (grounding)"),
    ToolItem(
        name="Agent/Task", kind="agent", mutating=False, note="dispatch a subagent in fresh context"
    ),
    ToolItem(name="NotebookEdit", kind="file", mutating=True, note="edit Jupyter notebook cells"),
    ToolItem(
        name="TodoWrite", kind="meta", mutating=False, note="track multi-step work in-session"
    ),
)


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
        note="frontmatter (skill metadata) only; bodies load on trigger",
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
        vendor_gaps=_vendor_gaps("subagents"),
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
            name="hooks",
            source="ai/agents/shared/hooks/*.sh",
            mode=LoadMode.harness,
            est_tokens=0,
            count=len(hooks),
            note="pre-tool guards + verify-before-done (K1) + format/notify",
            vendor_gaps=_vendor_gaps("hooks"),
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
    # Show "P?"/"G?" on a zero count, never a hardcoded historical number — a gauge
    # that fabricates on failure (regex break, missing doc) is worse than one that
    # admits it doesn't know (P7/G13: fail loud, never silent in your own layer).
    p_range = f"P1-P{principles}" if principles else "P?"
    g_range = f"G1-G{gates}" if gates else "G?"
    return (
        MapColumn(
            name="Doctrine",
            ids=f"K1-K8 · {p_range}",
            source="rules.md · engineering-philosophy.md",
        ),
        MapColumn(
            name="Enforcement",
            ids=g_range,
            source="engineering-gates.md",
        ),
        MapColumn(name="Defense in depth", ids="L0-L5", source="how-we-build.md"),
        MapColumn(
            name="Tools",
            ids=f"{skills} lenses/skills",
            source="code-health-portfolio.md",
        ),
    )


def _tools(root: Path) -> tuple[ToolItem, ...]:
    """The agent's tool surface: built-in tools + a derived line for wired MCP servers."""
    mcp = _mcp_count(root)
    mcp_item = ToolItem(
        name="MCP",
        kind="mcp",
        mutating=False,
        note=f"{mcp} server(s) wired (ctx7, browser, …); tools loaded on demand",
    )
    return (*_BUILTIN_TOOLS, mcp_item)


def _harness_layers(root: Path) -> tuple[HarnessLayer, ...]:
    """The five-layer harness model (orchestration → observability), mapped to this repo."""
    skills = len(sorted((root / "ai" / "skills").glob("*/SKILL.md")))
    hooks = len(sorted((root / "ai" / "agents" / "shared" / "hooks").glob("*.sh")))
    tools = len(_BUILTIN_TOOLS)
    mcp = _mcp_count(root)
    return (
        HarnessLayer(
            name="1 · Tool orchestration",
            pieces=f"{tools} built-in tools · {mcp} MCP server(s)",
            note="what the agent can do; mutating tools (Bash/Edit/Write) are gated",
        ),
        HarnessLayer(
            name="2 · Verification loops",
            pieces="verify-before-done (K1) · gates G1-G14 · review · adversarial-assessor",
            note="catch a failure before it compounds; separate grader from generator",
        ),
        HarnessLayer(
            name="3 · Context & memory",
            pieces=f"kernel K1-K8 · {skills} skills · reference docs · MEMORY.md",
            note="curated, repo-owned, version-controlled — not tool-private memory",
        ),
        HarnessLayer(
            name="4 · Guardrails",
            pieces=f"{hooks} hooks · deny-vocabulary · permission profile",
            note="block destructive/sensitive actions at the pre-tool boundary",
        ),
        HarnessLayer(
            name="5 · Observability",
            pieces="verify-before-done.log · structlog at service boundaries",
            note="see the gate fire; make a silent degradation loud (P9/G13)",
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
    return InstructionsManifest(
        items=items,
        columns=_map_columns(dotfiles_dir),
        tools=_tools(dotfiles_dir),
        layers=_harness_layers(dotfiles_dir),
        doctrine=DOCTRINE,
        routing=CATECHISM,
    )
