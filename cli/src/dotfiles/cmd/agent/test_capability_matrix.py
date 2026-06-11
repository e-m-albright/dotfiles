"""Tests for the provenance-backed capability matrix.

Three halves:
- **Invariants** — every capability covers all 5 agents; every supported cell
  carries a receipt (a local probe and/or a source URL); the agy corrections hold.
- **Tethering** — a live probe runs against an installed binary (skipped if absent)
  to prove the matrix matches reality, not a page.
- **Drift** — docs/knowledge/agent-fleet.md mirrors the matrix status tokens.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from dotfiles.agent import AGENTS
from dotfiles.cmd.agent.capability_matrix import (
    CAPABILITY_MATRIX,
    capability_rows,
    fleet_doc_stale_days,
    receipts,
)

_REPO = Path(__file__).resolve().parents[5]

# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


def test_every_capability_covers_all_agents() -> None:
    for cap in CAPABILITY_MATRIX:
        assert set(cap.cells) == set(AGENTS), f"{cap.key} missing an agent"


def test_expected_capability_set() -> None:
    keys = {c.key for c in CAPABILITY_MATRIX}
    # the 8 surfaces + the 2026-era categories the user asked for
    for expected in (
        "rules",
        "skills",
        "subagents",
        "mcp",
        "hooks",
        "statusline",
        "permissions",
        "plugins",
        "dynamic-workflows",
        "memory",
        "output-styles",
        "slash-commands",
        "sandboxing",
        "model-routing",
    ):
        assert expected in keys, f"missing capability row: {expected}"


def test_supported_cells_carry_a_receipt() -> None:
    """No hand-asserted support: every yes/beta/ext cell has a probe OR a source."""
    for cap in CAPABILITY_MATRIX:
        for agent, cell in cap.cells.items():
            if cell.status in ("yes", "beta", "ext"):
                assert cell.test or cell.src, f"{cap.key}/{agent} = {cell.status} with no receipt"


def test_antigravity_corrections_hold() -> None:
    """The cells I wrongly marked unsupported are now 'yes', proven by agy's binary."""
    by_key = {c.key: c for c in CAPABILITY_MATRIX}
    for key in ("skills", "subagents", "hooks", "statusline"):
        cell = by_key[key].cells["gemini"]  # the ~/.gemini slot = Antigravity
        assert cell.status == "yes", f"agy {key} should be yes, is {cell.status}"
        assert cell.test, f"agy {key} should carry a local probe"


def test_claude_dynamic_workflows_is_yes() -> None:
    # local proof wins over the doc-less web result
    dw = next(c for c in CAPABILITY_MATRIX if c.key == "dynamic-workflows")
    assert dw.cells["claude"].status == "yes"


def test_receipts_returns_only_cells_with_proof() -> None:
    for _cap, _agent, cell in receipts():
        assert cell.test or cell.src


# ---------------------------------------------------------------------------
# Tethering — prove a claim against a real installed binary (skip if absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("agy") is None, reason="agy not installed")
def test_agy_statusline_probe_actually_passes() -> None:
    """The matrix says agy statusline = yes; prove it on the installed binary."""
    agy = shutil.which("agy")
    assert agy is not None
    out = subprocess.run(
        ["strings", str(Path(agy).resolve())], capture_output=True, text=True, check=False
    )
    assert "statusline" in out.stdout.lower(), "agy binary should reference statusline"


# ---------------------------------------------------------------------------
# Drift gate: agent-fleet.md matrix tokens mirror the code
# ---------------------------------------------------------------------------

_HEADER_AGENT = {
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "antigravity": "gemini",
    "pi": "pi",
    "hermes": "hermes",
}


def _matrix_rows(text: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.startswith("| Capability") and "Antigravity" in ln
    )
    header = [c.strip().lower() for c in lines[header_idx].strip("|").split("|")]
    rows = []
    for ln in lines[header_idx + 2 :]:
        if not ln.startswith("|"):
            break
        rows.append([c.strip() for c in ln.strip("|").split("|")])
    return header, rows


def test_doc_table_mirrors_matrix_status() -> None:
    text = (_REPO / "docs" / "knowledge" / "agent-fleet.md").read_text()
    header, rows = _matrix_rows(text)
    col = {_HEADER_AGENT[h]: i for i, h in enumerate(header) if h in _HEADER_AGENT}
    assert set(col) == set(AGENTS), "doc matrix missing a vendor column"
    by_key = {c.key: c for c in CAPABILITY_MATRIX}
    seen: set[str] = set()
    for cells in rows:
        key = cells[0].strip().lower()
        if key not in by_key:
            continue
        seen.add(key)
        for agent, idx in col.items():
            token = cells[idx].strip().lower().split()[0]  # leading status word
            assert token == by_key[key].cells[agent].status, (
                f"drift: {key}/{agent} doc={token} code={by_key[key].cells[agent].status}"
            )
    assert seen == set(by_key), f"doc rows {seen} != matrix keys {set(by_key)}"


# ---------------------------------------------------------------------------
# Doc staleness helpers
# ---------------------------------------------------------------------------


def test_staleness_counts_days(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "knowledge" / "agent-fleet.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("> **Last reviewed**: 2026-06-01\n")
    assert fleet_doc_stale_days(tmp_path, date(2026, 6, 9)) == 8


def test_staleness_none_without_stamp(tmp_path: Path) -> None:
    assert fleet_doc_stale_days(tmp_path, date(2026, 6, 9)) is None


def test_capability_rows_render_shape() -> None:
    rows = capability_rows()
    assert len(rows) == len(CAPABILITY_MATRIX)
    assert all(set(r.cells) == set(AGENTS) for r in rows)
