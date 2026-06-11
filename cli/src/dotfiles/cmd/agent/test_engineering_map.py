"""Drift gate for the ENGINEERING.md ID system (closes assessor finding F6).

The map's K/P/G IDs are load-bearing — the verify hook, `agent instructions`, and
the routing table all cite them — but they live as hand-listed table rows in
`ENGINEERING.md` while the *counts* are derived elsewhere (the manifest regexes the
numbered headers in the source docs). Nothing cross-checked the two, so adding G15
to the gates doc would let the manifest print "G1-G15" while the map still said
"G1-G14" — exactly the silent drift G11 ("one source, translated, drift-gated")
exists to prevent. This test is that gate.
"""

from __future__ import annotations

import re
from pathlib import Path

from dotfiles.cmd.agent.instructions import build_manifest

_REPO = Path(__file__).resolve().parents[5]


def _table_ids(doc: str, letter: str) -> list[int]:
    """The IDs listed in ENGINEERING.md's tables, e.g. every `| **G7** |` → 7."""
    return [int(n) for n in re.findall(rf"\|\s*\*\*{letter}(\d+)\*\*\s*\|", doc)]


def _numbered_headers(doc: str) -> int:
    """Numbered `## N.` / `### N.` headers — the manifest's own count source."""
    return len(re.findall(r"(?m)^#{2,3} \d+\. ", doc))


def test_map_ids_are_contiguous_and_match_their_source_docs() -> None:
    eng = (_REPO / "ENGINEERING.md").read_text()
    philosophy = (_REPO / "docs" / "engineering-philosophy.md").read_text()
    gates = (_REPO / "docs" / "knowledge" / "engineering-gates.md").read_text()

    kernel = _table_ids(eng, "K")
    principles = _table_ids(eng, "P")
    gateids = _table_ids(eng, "G")

    # IDs must be contiguous 1..n (no gaps, no dupes) in the map's own tables.
    assert kernel == list(range(1, 9)), f"kernel table must list K1..K8, got {kernel}"
    assert principles == list(range(1, len(principles) + 1)), f"P-IDs not contiguous: {principles}"
    assert gateids == list(range(1, len(gateids) + 1)), f"G-IDs not contiguous: {gateids}"

    # The drift gate: the map's table sizes must match the source docs the manifest
    # counts from — so a new principle/gate can't land in one place but not the other.
    assert len(principles) == _numbered_headers(philosophy), (
        "ENGINEERING.md P-table drifted from engineering-philosophy.md"
    )
    assert len(gateids) == _numbered_headers(gates), (
        "ENGINEERING.md G-table drifted from engineering-gates.md"
    )


def test_manifest_columns_agree_with_the_map() -> None:
    eng = (_REPO / "ENGINEERING.md").read_text()
    principles = _table_ids(eng, "P")
    gateids = _table_ids(eng, "G")
    columns = {c.name: c.ids for c in build_manifest(_REPO).columns}

    # The live-derived manifest labels must match the map's hand-listed ranges —
    # this is what catches the `P{n or 12}` fallback lying after a regex break.
    assert columns["Doctrine"].endswith(f"P1-P{len(principles)}")
    assert columns["Enforcement"] == f"G1-G{len(gateids)}"
