"""Tests for the cockpit drill-downs (detail.py) — projections, not new probes."""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles.agent import AGENTS
from dotfiles.cmd.agent.detail import (
    K1_EVENTS,
    K1_SCRIPT,
    deny_list,
    hook_wirings,
    k1_events_in,
    k1_liveness,
    subagent_details,
)
from dotfiles.cmd.agent.fleet import build_fleet

_REPO = Path(__file__).resolve().parents[5]


def test_repo_claude_hooks_wire_k1_in_both_events() -> None:
    """The durable gate: the canonical ai/agents/claude/hooks.json MUST wire the K1
    verify hook in both Stop and SubagentStop, so setup always deploys a live gate.
    Pairs with k1_liveness (which checks the deployed copy) to close the loop —
    if anyone ever stops wiring K1 at the source, this fails."""
    events = k1_events_in(_REPO / "ai" / "agents" / "claude" / "hooks.json")
    for event in K1_EVENTS:
        assert events[event], f"ai/agents/claude/hooks.json must wire {K1_SCRIPT} in {event}"


def _write_claude_settings(home: Path, hooks: dict[str, object]) -> None:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"hooks": hooks}))


def _k1_entry() -> dict[str, object]:
    return {"matcher": "", "hooks": [{"type": "command", "command": f"bash path/{K1_SCRIPT}"}]}


def test_k1_live_when_wired_in_both_events(tmp_path: Path) -> None:
    _write_claude_settings(tmp_path, {"Stop": [_k1_entry()], "SubagentStop": [_k1_entry()]})
    k1 = k1_liveness(tmp_path)
    assert k1.live
    assert k1.events == {"Stop": True, "SubagentStop": True}


def test_k1_not_live_when_subagentstop_drops_it(tmp_path: Path) -> None:
    # The exact drift the probe exists to catch: Stop kept, SubagentStop rewritten.
    _write_claude_settings(tmp_path, {"Stop": [_k1_entry()], "SubagentStop": []})
    k1 = k1_liveness(tmp_path)
    assert not k1.live
    assert k1.events["Stop"] is True
    assert k1.events["SubagentStop"] is False


def test_k1_not_live_when_settings_absent(tmp_path: Path) -> None:
    k1 = k1_liveness(tmp_path)  # no settings.json at all
    assert not k1.live


def test_k1_structural_not_substring(tmp_path: Path) -> None:
    # The script name appears in the file (e.g. a stray top-level field) but NOT as
    # a command value inside a Stop/SubagentStop entry — a grep would false-positive;
    # the structural probe must not.
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(
            {"_note": f"we used to wire {K1_SCRIPT}", "hooks": {"Stop": [], "SubagentStop": []}}
        )
    )
    assert not k1_liveness(tmp_path).live


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
