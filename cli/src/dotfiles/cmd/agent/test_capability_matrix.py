"""Tests for the cross-vendor capability matrix + its drift gate.

Two halves:
- **Probes** — a fully-deployed fake home lights every target cell; an empty
  home shows every required cell as a gap. No real home is touched.
- **Drift** — the prose table in docs/knowledge/agent-fleet.md is parsed and
  asserted equal to CAPABILITY_MATRIX, cell for cell, so the doc and the code
  can never silently diverge (same discipline as test_deny_commands_sync.py).
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from dotfiles.agent import AGENTS
from dotfiles.cmd.agent.capability_matrix import (
    CAPABILITY_MATRIX,
    CapabilityMatrixService,
    fleet_doc_stale_days,
)

_REPO = Path(__file__).resolve().parents[5]

# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------


def test_every_capability_covers_every_agent() -> None:
    for cap in CAPABILITY_MATRIX:
        assert set(cap.intents) == set(AGENTS), f"{cap.key} missing an agent"


def test_pi_is_the_only_canonical_statusline() -> None:
    statusline = next(c for c in CAPABILITY_MATRIX if c.key == "statusline")
    assert statusline.intents["pi"] == "canonical"
    assert statusline.intents["claude"] == "required"


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


def _deploy_full_home(home: Path, dotfiles: Path) -> None:
    """Write one artifact per target cell so every probe should fire."""
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "CLAUDE.md").write_text("# rules\n")
    (home / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "statusLine": {"type": "command", "command": "x"},
                "hooks": {"Stop": []},
                "permissions": {"allow": [], "deny": ["Bash(rm:*)"]},
            }
        )
    )
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"granola": {}}}))

    (home / ".codex").mkdir(parents=True)
    (home / ".codex" / "AGENTS.md").write_text("# rules\n")
    (home / ".codex" / "config.toml").write_text("[tui]\ntheme='x'\n[mcp_servers.granola]\n")
    (home / ".codex" / "hooks.json").write_text(json.dumps({"hooks": {}}))
    (home / ".codex" / "rules").mkdir()
    (home / ".codex" / "rules" / "default.rules").write_text("prefix_rule x\n")

    (home / ".cursor").mkdir(parents=True)
    (home / ".cursor" / "mcp.json").write_text(json.dumps({"mcpServers": {"context7": {}}}))
    (home / ".cursor" / "cli-config.json").write_text(
        json.dumps({"permissions": {"allow": [], "deny": ["Shell(rm)"]}})
    )

    (home / ".gemini").mkdir(parents=True)
    (home / ".gemini" / "GEMINI.md").write_text("# rules\n")
    (home / ".gemini" / "settings.json").write_text(
        json.dumps({"mcpServers": {"context7": {}}, "tools": {"exclude": ["run_shell_command"]}})
    )

    (home / ".pi" / "agent" / "extensions").mkdir(parents=True)
    (home / ".pi" / "agent" / "AGENTS.md").write_text("# rules\n")
    (home / ".pi" / "agent" / "extensions" / "git-status.ts").write_text("export {}\n")
    (home / ".pi" / "agent" / "permission-policy.json").write_text(json.dumps({"denyCommands": []}))

    # Skills (claude/cursor own dirs; codex+pi share .agents/skills) + subagents.
    for skills_dir in (".claude/skills", ".cursor/skills-cursor", ".agents/skills"):
        (home / skills_dir / "demo").mkdir(parents=True)
        (home / skills_dir / "demo" / "SKILL.md").write_text("---\nname: demo\n---\n")
    for agents_dir in (".claude/agents", ".codex/agents", ".pi/agent/agents"):
        (home / agents_dir).mkdir(parents=True, exist_ok=True)
        (home / agents_dir / "demo.md").write_text("# demo\n")
    (home / ".claude" / "plugins").mkdir(parents=True)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text(
        json.dumps({"plugins": {"superpowers@official": [{"version": "1.0"}]}})
    )

    (dotfiles / "ai" / "agents" / "cursor" / "rules").mkdir(parents=True)
    (dotfiles / "ai" / "agents" / "cursor" / "rules" / "shared-rules.mdc").write_text("x")
    (dotfiles / "ai" / "agents" / "cursor" / "hooks").mkdir(parents=True)
    (dotfiles / "ai" / "agents" / "cursor" / "hooks" / "hooks.json").write_text("{}")


def test_full_deploy_lights_every_target_cell(tmp_path: Path) -> None:
    home, dotfiles = tmp_path / "home", tmp_path / "dotfiles"
    _deploy_full_home(home, dotfiles)
    rows = {
        r.capability: r for r in CapabilityMatrixService(home=home, dotfiles_dir=dotfiles).rows()
    }
    for cap in CAPABILITY_MATRIX:
        for agent, intent in cap.intents.items():
            cell = rows[cap.key].cells[agent]
            if intent == "na":
                assert not cell.present, f"{cap.key}/{agent} n/a should not be present"
            else:
                assert cell.present, f"{cap.key}/{agent} target unmet despite deploy"


def test_empty_home_shows_required_cells_as_gaps(tmp_path: Path) -> None:
    home, dotfiles = tmp_path / "home", tmp_path / "dotfiles"
    rows = {
        r.capability: r for r in CapabilityMatrixService(home=home, dotfiles_dir=dotfiles).rows()
    }
    for cap in CAPABILITY_MATRIX:
        for agent, intent in cap.intents.items():
            assert not rows[cap.key].cells[agent].present
            assert rows[cap.key].cells[agent].intent == intent


# ---------------------------------------------------------------------------
# Drift gate: docs/knowledge/agent-fleet.md must mirror CAPABILITY_MATRIX
# ---------------------------------------------------------------------------

_GLYPH_INTENT = {"✓": "required", "★": "canonical", "⊕": "different", "—": "na"}
_HEADER_AGENT = {
    "claude code": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "gemini": "gemini",
    "pi": "pi",
}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _lead_glyph(cell: str) -> str:
    for ch in cell:
        if ch in _GLYPH_INTENT:
            return ch
    raise AssertionError(f"no glyph in doc cell: {cell!r}")


def _contiguous_table(lines: list[str], start: int) -> list[list[str]]:
    """Parsed cells of consecutive ``| … |`` rows starting at *start*."""
    out: list[list[str]] = []
    for row in lines[start:]:
        if not row.startswith("|"):
            break
        out.append(_cells(row))
    return out


def _parse_doc_table(text: str) -> tuple[list[str], list[list[str]]]:
    """Return (header_cells, data_rows) of the capability table in agent-fleet.md."""
    lines = text.splitlines()
    headers = [
        i for i, ln in enumerate(lines) if ln.startswith("| Capability") and "Claude Code" in ln
    ]
    if not headers:
        raise AssertionError("capability table not found in agent-fleet.md")
    top = headers[0]
    return _cells(lines[top]), _contiguous_table(lines, top + 2)  # +2 skips |---| separator


def test_real_fleet_doc_has_a_review_stamp() -> None:
    # The live doc must carry a parseable 'Last reviewed' date for the warn.
    days = fleet_doc_stale_days(_REPO, date(2099, 1, 1))
    assert days is not None
    assert days > 0


def test_staleness_none_without_stamp(tmp_path: Path) -> None:
    assert fleet_doc_stale_days(tmp_path, date(2026, 6, 9)) is None


def test_staleness_counts_days(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "knowledge" / "agent-fleet.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("> **Last reviewed**: 2026-06-01 — refresh when…\n")
    assert fleet_doc_stale_days(tmp_path, date(2026, 6, 9)) == 8


def test_doc_table_mirrors_matrix() -> None:
    text = (_REPO / "docs" / "knowledge" / "agent-fleet.md").read_text()
    header, rows = _parse_doc_table(text)
    # Map each vendor column index by its header name.
    col_for_agent = {
        _HEADER_AGENT[h.lower()]: idx for idx, h in enumerate(header) if h.lower() in _HEADER_AGENT
    }
    assert set(col_for_agent) == set(AGENTS), "doc table is missing a vendor column"

    by_key = {cap.key: cap for cap in CAPABILITY_MATRIX}
    seen: set[str] = set()
    for cells in rows:
        key = re.split(r"\W+", cells[0].lower())[0]  # "Rules (instructions)" -> "rules"
        if key not in by_key:
            continue
        seen.add(key)
        for agent, col in col_for_agent.items():
            intent = _GLYPH_INTENT[_lead_glyph(cells[col])]
            assert intent == by_key[key].intents[agent], (
                f"drift: {key}/{agent} doc={intent} code={by_key[key].intents[agent]}"
            )
    assert seen == set(by_key), f"doc table rows {seen} != matrix keys {set(by_key)}"
