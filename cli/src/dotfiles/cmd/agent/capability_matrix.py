"""The cross-vendor capability matrix — provenance-backed, not hand-asserted.

Every cell is a VENDOR-CAPABILITY claim (does the tool support X?) that carries
its **receipt**: a local probe (a command that proves it on this machine — binary
`strings`, `--help` grep, config check) and/or a source URL. Nothing here is
"written on a page" — each `yes`/`beta` is either tested live or cited.

Reconciliation rule when a local probe and a doc disagree: **the local probe
wins** (it's what's installed). E.g. Claude dynamic-workflows is `yes` because
its binary ships `dynamic workflow`/`ultracode` strings (and we drive it via the
Workflow tool), even though there's no public feature doc.

Status: yes (GA) · beta (preview/partial/auto-only) · ext (only via an
extension, e.g. Pi) · no (proven absent, with evidence) · unverified (no
first-party source AND not locally probeable). Glyphs render in
``dotfiles agent overview``; the full evidence lives in docs/knowledge/agent-fleet.md.

Run the local probes with ``dotfiles agent capabilities --verify`` to keep the
matrix tethered to reality.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import AGENTS, VENDORS

CellStatus = Literal["yes", "beta", "ext", "no", "unverified"]


class Cell(BaseModel):
    """One (capability, vendor) claim plus its receipt(s)."""

    model_config = ConfigDict(frozen=True)

    status: CellStatus
    test: str = ""  # a shell command that PROVES the claim on this machine
    src: str = ""  # a source URL (documentary receipt) where no local test fits


class Capability(BaseModel):
    """One capability row: what it is + a cell per vendor."""

    model_config = ConfigDict(frozen=True)

    key: str
    note: str  # one line: what the capability is
    cells: dict[str, Cell]


def _row(
    key: str,
    note: str,
    claude: Cell,
    codex: Cell,
    cursor: Cell,
    antigravity: Cell,
    pi: Cell,
    hermes: Cell,
) -> Capability:
    return Capability(
        key=key,
        note=note,
        cells={
            "claude": claude,
            "codex": codex,
            "cursor": cursor,
            "gemini": antigravity,  # the ~/.gemini slot is Antigravity (agy)
            "pi": pi,
            "hermes": hermes,
        },
    )


def _c(status: CellStatus, test: str = "", src: str = "") -> Cell:
    return Cell(status=status, test=test, src=src)


# 14 capabilities x 6 vendors. Order: context surfaces, integration, UX/safety,
# extensibility, then the 2026-era categories.
CAPABILITY_MATRIX: tuple[Capability, ...] = (
    _row(
        "rules",
        "always-on instruction file (CLAUDE.md/AGENTS.md/.mdc)",
        _c("yes", "test -f ~/.claude/CLAUDE.md"),
        _c("yes", "test -f ~/.codex/AGENTS.md"),
        _c("yes", "test -d ~/.cursor", "https://cursor.com/docs/cli/using"),
        _c("yes", "test -f ~/.gemini/AGENTS.md"),
        _c("yes", "pi --help | grep -q -- --no-context-files"),
        _c("yes", "test -f ~/.hermes/SOUL.md"),  # + project AGENTS.md/CLAUDE.md auto-injected
    ),
    _row(
        "skills",
        "portable SKILL.md capability packs",
        _c("yes", "test -d ~/.claude/skills"),
        _c("yes", "strings $(which codex) | grep -qi SKILL.md"),
        _c("yes", "test -d ~/.cursor/skills-cursor", "https://cursor.com/changelog/2-4"),
        _c("yes", "strings $(which agy) | grep -qi /skills"),
        _c("yes", "pi --help | grep -q -- --skill"),
        _c("yes", "test -d ~/.hermes/skills"),
    ),
    _row(
        "subagents",
        "isolated-context delegated agents",
        _c("yes", "strings $(which claude) | grep -qi subagent"),
        _c("yes", "strings $(which codex) | grep -qi subagent"),
        _c("yes", "test -d ~/.cursor/agents", "https://cursor.com/docs/subagents"),
        _c("yes", "strings $(which agy) | grep -qi subagent"),
        _c("ext", "", "https://github.com/nicobailon/pi-subagents"),
        _c("yes", "test -f ~/.hermes/hermes-agent/tools/delegate_tool.py"),  # delegate_task
    ),
    _row(
        "mcp",
        "Model Context Protocol servers",
        _c("yes", "claude --help | grep -qi mcp"),
        _c("yes", "codex --help | grep -qi mcp"),
        _c("yes", "test -f ~/.cursor/mcp.json"),
        _c("yes", "test -f ~/.gemini/config/mcp_config.json"),
        _c("no", "pi --help | grep -qi mcp", "https://github.com/earendil-works/pi"),
        _c(
            "beta", "test -d ~/.hermes/hermes-agent/optional-mcps"
        ),  # runtime registry, no static cfg
    ),
    _row(
        "hooks",
        "deterministic lifecycle shell hooks",
        _c("yes", "grep -q hooks ~/.claude/settings.json"),
        _c("yes", "strings $(which codex) | grep -qi /hooks"),
        _c("yes", "", "https://cursor.com/docs/hooks"),
        _c("yes", "strings $(which agy) | grep -qi /hooks"),
        _c(
            "ext",
            "test -f ~/.pi/agent/extensions/safe-git.ts",
            "https://pi.dev/docs/latest/extensions",
        ),
        _c(
            "beta", "test -d ~/.hermes/hooks"
        ),  # hooks dir seeded; schema undocumented, we don't deploy
    ),
    _row(
        "statusline",
        "custom terminal status footer",
        _c("yes", "strings $(which claude) | grep -qi statusline"),
        _c("yes", "grep -q status_line ~/.codex/config.toml"),
        _c("beta", "", "https://cursor.com/changelog/04-14-26"),
        _c("yes", "strings $(which agy) | grep -qi statusline"),
        _c("ext", "test -f ~/.pi/agent/extensions/git-status.ts"),
        _c("unverified", ""),  # TUI footer is fixed; no custom statusline surface found
    ),
    _row(
        "permissions",
        "tool/command allow-deny gating",
        _c("yes", "grep -q permissions ~/.claude/settings.json"),
        _c("yes", "codex --help | grep -qi sandbox"),
        _c("yes", "test -f ~/.cursor/cli-config.json"),
        _c("yes", "grep -q exclude ~/.gemini/settings.json"),
        _c("ext", "test -f ~/.pi/agent/permission-policy.json"),
        _c(
            "beta", "test -f ~/.hermes/hermes-agent/tools/skills_guard.py"
        ),  # tool gating + Docker sandbox
    ),
    _row(
        "plugins",
        "first-party plugin/marketplace",
        _c("yes", "claude --help | grep -qi plugin"),
        _c("yes", "strings $(which codex) | grep -qi plugin"),
        _c("yes", "", "https://cursor.com/changelog/2-5"),
        _c("yes", "agy plugin list"),
        _c("yes", "pi list"),
        _c("yes", "test -d ~/.hermes/hermes-agent/plugins"),  # plugins/ + skills marketplace
    ),
    _row(
        "dynamic-workflows",
        "agent-authored JS orchestration over many subagents",
        _c("yes", "strings $(which claude) | grep -qi 'dynamic workflow'"),
        _c("no", "", "https://developers.openai.com/codex/changelog"),
        _c("unverified", ""),
        _c("no", "", "https://antigravity.google/docs/rules-workflows"),
        _c("yes", "pi --help | grep -qi extension", "https://pi.dev/docs/latest/extensions"),
        _c("beta", "test -f ~/.hermes/hermes-agent/batch_runner.py"),  # delegate_task + batch/cron
    ),
    _row(
        "memory",
        "persistent cross-session memory",
        _c("yes", "strings $(which claude) | grep -qi memory"),
        _c("beta", "", "https://developers.openai.com/codex/changelog"),
        _c("unverified", ""),
        _c("yes", "strings $(which agy) | grep -qi /memory"),
        _c("yes", "pi --help | grep -q -- --resume"),
        _c("yes", "test -d ~/.hermes/memories"),  # MEMORY.md / USER.md
    ),
    _row(
        "output-styles",
        "configurable response style/persona",
        _c(
            "beta",
            "strings $(which claude) | grep -qi outputstyle",
            "https://docs.claude.com/en/docs/claude-code/output-styles",
        ),
        _c("yes", "strings $(which codex) | grep -qi personality"),
        _c("no", "", "https://cursor.com/docs/cli/reference"),
        _c("no", ""),
        _c("yes", "pi --help | grep -qi theme"),
        _c("yes", "test -f ~/.hermes/SOUL.md"),  # SOUL.md = editable persona/identity
    ),
    _row(
        "slash-commands",
        "custom /command files",
        _c("yes", "claude --help | grep -qi slash"),
        _c("yes", "strings $(which codex) | grep -qi ARGUMENTS"),
        _c("yes", "", "https://cursor.com/docs/cli/reference/slash-commands"),
        _c("yes", "strings $(which agy) | grep -qi /agents"),
        _c("yes", "", "https://pi.dev/docs/latest/prompt-templates"),
        _c("yes", "", "https://hermes-agent.nousresearch.com/docs/reference/cli-commands"),
    ),
    _row(
        "sandboxing",
        "built-in command sandbox",
        _c("yes", "claude --help | grep -qi sandbox"),
        _c("yes", "codex --help | grep -qi sandbox"),
        _c("yes", "cursor-agent --help | grep -qi sandbox"),
        _c("yes", "agy --help 2>&1 | grep -qi sandbox"),
        _c("no", "pi --help | grep -qi sandbox", "https://pi.dev/docs/latest/security"),
        _c("yes", "test -f ~/.hermes/hermes-agent/Dockerfile"),  # Docker container isolation
    ),
    _row(
        "model-routing",
        "fallback chain / multi-model routing",
        _c("yes", "claude --help | grep -q -- --fallback-model"),
        _c("yes", "codex --help | grep -qi model"),
        _c("beta", "cursor-agent --help | grep -q -- --model"),
        _c("beta", "agy --help 2>&1 | grep -qi model"),
        _c("beta", "pi --help | grep -q -- --models"),
        _c(
            "yes", "", "https://hermes-agent.nousresearch.com/docs/user-guide/configuration"
        ),  # fallback_model
    ),
)


# ---------------------------------------------------------------------------
# Render rows (consumed by the overview)
# ---------------------------------------------------------------------------


class CapabilityRow(BaseModel):
    """One capability across all vendors, for rendering."""

    model_config = ConfigDict(frozen=True)

    capability: str
    note: str
    cells: dict[str, Cell]


def capability_rows() -> list[CapabilityRow]:
    """The matrix as render rows (static — provenance carried per cell)."""
    return [
        CapabilityRow(capability=cap.key, note=cap.note, cells=dict(cap.cells))
        for cap in CAPABILITY_MATRIX
    ]


def receipts() -> list[tuple[str, str, Cell]]:
    """(capability, agent, cell) for every cell that has a test or source — the evidence."""
    out: list[tuple[str, str, Cell]] = []
    for cap in CAPABILITY_MATRIX:
        for agent in AGENTS:
            cell = cap.cells[agent]
            if cell.test or cell.src:
                out.append((cap.key, agent, cell))
    return out


# ---------------------------------------------------------------------------
# Doc generation: the agent-fleet.md matrix table is GENERATED from this module
# (between the markers below) by `dotfiles agent setup` — never hand-edited.
# ---------------------------------------------------------------------------

DOC_TABLE_BEGIN = "<!-- capability-matrix:begin · generated, do not hand-edit -->"
DOC_TABLE_END = "<!-- capability-matrix:end -->"


def doc_matrix_table() -> str:
    """The capability matrix as a markdown table — the doc's generated block."""
    header = "| Capability | " + " | ".join(v.display_name for v in VENDORS) + " |"
    rule = "|---" * (len(VENDORS) + 1) + "|"
    rows = [
        "| " + " | ".join([cap.key, *(cap.cells[v.name].status for v in VENDORS)]) + " |"
        for cap in CAPABILITY_MATRIX
    ]
    return "\n".join([header, rule, *rows])


def doc_table_block() -> str:
    """The full generated block, markers included."""
    return f"{DOC_TABLE_BEGIN}\n{doc_matrix_table()}\n{DOC_TABLE_END}"


def update_fleet_doc(dotfiles_dir: Path) -> bool | None:
    """Rewrite the generated matrix block in agent-fleet.md.

    Returns True if the doc changed, False if already current, None when the
    doc or its markers are missing (nothing to do — surfaced by the drift test,
    not silently created here).
    """
    doc_path = dotfiles_dir.joinpath(*FLEET_DOC_REL)
    text = _read_text(doc_path)
    begin, end = text.find(DOC_TABLE_BEGIN), text.find(DOC_TABLE_END)
    if begin < 0 or end < 0:
        return None
    current = text[begin : end + len(DOC_TABLE_END)]
    block = doc_table_block()
    if current == block:
        return False
    doc_path.write_text(text[:begin] + block + text[end + len(DOC_TABLE_END) :])
    return True


# ---------------------------------------------------------------------------
# Doc staleness (warn when agent-fleet.md's review lapses)
# ---------------------------------------------------------------------------

FLEET_DOC_REL = ("docs", "knowledge", "agent-fleet.md")
FLEET_STALE_DAYS = 90
_REVIEWED_RE = re.compile(r"Last reviewed\D*(\d{4})-(\d{2})-(\d{2})")


def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""


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
