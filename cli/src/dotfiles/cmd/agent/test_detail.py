"""Tests for the cockpit drill-downs (detail.py) — projections, not new probes."""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles.agent import AGENTS
from dotfiles.cmd.agent.detail import deny_list, hook_wirings, subagent_details
from dotfiles.cmd.agent.fleet import build_fleet

# ---------------------------------------------------------------------------
# Subagents
# ---------------------------------------------------------------------------


def _seed_subagent(dotfiles: Path, name: str, description: str) -> None:
    root = dotfiles / "ai" / "subagents"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n"
    )


def test_subagent_details_empty_without_canonical_dir(tmp_path: Path) -> None:
    assert subagent_details(dotfiles_dir=tmp_path / "d", home=tmp_path / "h") == []


def test_subagent_details_carry_description_and_deploy_cells(tmp_path: Path) -> None:
    dotfiles, home = tmp_path / "d", tmp_path / "h"
    _seed_subagent(dotfiles, "debugger", "Root-cause analysis. Deep dives.")
    (home / ".claude" / "agents").mkdir(parents=True)
    (home / ".claude" / "agents" / "debugger.md").write_text("# d")
    details = subagent_details(dotfiles_dir=dotfiles, home=home)
    assert len(details) == 1
    d = details[0]
    assert d.description.startswith("Root-cause")
    assert d.cells["claude"] is True
    assert d.cells["codex"] is False
    # Only vendors with a subagents Deploy stance appear as cells.
    assert "gemini" not in d.cells
    assert "hermes" not in d.cells


def test_subagent_details_sorted_by_name(tmp_path: Path) -> None:
    dotfiles = tmp_path / "d"
    for name in ("zeta", "alpha"):
        _seed_subagent(dotfiles, name, "x" * 20)
    names = [d.name for d in subagent_details(dotfiles_dir=dotfiles, home=tmp_path / "h")]
    assert names == ["alpha", "zeta"]


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def test_hook_wirings_cover_every_vendor(tmp_path: Path) -> None:
    fleet = build_fleet(home=tmp_path, dotfiles_dir=tmp_path)
    wirings = {w.vendor: w for w in hook_wirings(fleet, home=tmp_path)}
    assert set(wirings) == set(AGENTS)
    # Local stances surface their reason; the intent vendors report wiring.
    assert wirings["gemini"].stance == "local"
    assert wirings["gemini"].note
    assert wirings["claude"].stance == "deploy"
    assert wirings["claude"].wired == ()
    # Pi's hooks are an extension deploy, not shared-intent wiring.
    assert wirings["pi"].note == "extension"


def test_hook_wirings_report_live_intents(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"hooks": "guard-sensitive-file.sh notify.sh"}')
    fleet = build_fleet(home=tmp_path, dotfiles_dir=tmp_path)
    claude = next(w for w in hook_wirings(fleet, home=tmp_path) if w.vendor == "claude")
    assert claude.wired == ("guard-file", "notify")


# ---------------------------------------------------------------------------
# Permissions / deny floor
# ---------------------------------------------------------------------------


def test_deny_list_reads_entries_verbatim(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"permissions": {"allow": ["Bash(ls:*)"], "deny": ["Bash(sudo:*)", "Bash(rm -rf:*)"]}}
        )
    )
    result = deny_list("Claude Code (deployed)", settings)
    assert result is not None
    assert result.entries == ("Bash(sudo:*)", "Bash(rm -rf:*)")


def test_deny_list_none_when_config_absent(tmp_path: Path) -> None:
    assert deny_list("x", tmp_path / "missing.json") is None
