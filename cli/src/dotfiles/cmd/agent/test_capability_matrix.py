"""Tests for the provenance-backed capability matrix.

Three halves:
- **Invariants** — every capability covers all 5 agents; every supported cell
  carries a receipt (a local probe and/or a source URL); the agy corrections hold.
- **Tethering** — a live probe runs against an installed binary (skipped if absent)
  to prove the matrix matches reality, not a page.
- **Drift** — docs/knowledge/agent-fleet.md carries the generated matrix block
  verbatim (rewritten by `dotfiles agent setup`, never hand-edited).
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
    DOC_TABLE_BEGIN,
    DOC_TABLE_END,
    capability_rows,
    doc_matrix_table,
    doc_table_block,
    fleet_doc_stale_days,
    receipts,
    update_fleet_doc,
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
# Drift gate: the agent-fleet.md matrix table is the GENERATED block, verbatim
# ---------------------------------------------------------------------------


def test_doc_table_is_the_generated_block_verbatim() -> None:
    """agent-fleet.md's matrix is generated from this module (`dotfiles agent
    setup` rewrites it between the markers). Exact equality — a hand edit or a
    matrix change without regeneration both fail here."""
    text = (_REPO / "docs" / "knowledge" / "agent-fleet.md").read_text()
    assert doc_table_block() in text, (
        "agent-fleet.md capability table is stale or hand-edited — run `dotfiles agent setup`"
    )


def test_update_fleet_doc_rewrites_only_the_marked_block(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "knowledge" / "agent-fleet.md"
    doc.parent.mkdir(parents=True)
    stale = f"prose above\n\n{DOC_TABLE_BEGIN}\nOLD TABLE\n{DOC_TABLE_END}\n\nprose below\n"
    doc.write_text(stale)
    assert update_fleet_doc(tmp_path) is True
    text = doc.read_text()
    assert doc_table_block() in text
    assert text.startswith("prose above")
    assert text.endswith("prose below\n")
    # Idempotent: a second run reports no change.
    assert update_fleet_doc(tmp_path) is False


def test_update_fleet_doc_without_markers_is_a_loud_no_op(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "knowledge" / "agent-fleet.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("no markers here\n")
    assert update_fleet_doc(tmp_path) is None
    assert doc.read_text() == "no markers here\n"


def test_doc_matrix_table_covers_every_row_and_vendor() -> None:
    table = doc_matrix_table()
    lines = table.splitlines()
    assert len(lines) == 2 + len(CAPABILITY_MATRIX)  # header + rule + one row per capability
    for cap in CAPABILITY_MATRIX:
        row = next(ln for ln in lines if ln.startswith(f"| {cap.key} |"))
        cells = [c.strip() for c in row.strip("|").split("|")][1:]
        assert cells == [cap.cells[a].status for a in AGENTS]


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


# ---------------------------------------------------------------------------
# verify-probe teeth: a tether is only a tether if disagreement can FAIL
# ---------------------------------------------------------------------------


def test_verify_returns_drift_count_so_callers_can_fail() -> None:
    """With every probe exiting 0, the proven-`no` cells (which expect absent)
    disagree → the function must report that drift, not swallow it."""
    from dotfiles.cmd.agent.render.health import verify_capability_probes
    from dotfiles.testing.fakes import FakeProcessRunner

    drift = verify_capability_probes(FakeProcessRunner())  # all probes "present"
    no_cells_with_tests = sum(1 for _c, _a, cell in receipts() if cell.status == "no" and cell.test)
    assert drift == no_cells_with_tests
    assert drift > 0  # there is at least one proven-absent cell with a probe


def test_verify_returns_zero_when_every_probe_agrees() -> None:
    """Script the proven-`no` probes to fail (absent) and all supported probes to
    pass (present): full agreement → drift 0, so the command exits clean."""
    from dotfiles.cmd.agent.render.health import verify_capability_probes
    from dotfiles.testing.fakes import FakeProcessRunner

    runner = FakeProcessRunner()
    for _cap, _agent, cell in receipts():
        if cell.status == "no" and cell.test:
            runner.script(("bash", "-lc", cell.test), exit_code=1)
    assert verify_capability_probes(runner) == 0


# (test_have_implies_can_for_the_whole_registry) and is additionally enforced at
# runtime by fleet.build_fleet, which raises FleetInvariantError on violation.
