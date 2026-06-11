"""Tests for the fleet model — the single (vendor, surface) source of truth.

Two halves: the probe engine's HAVE semantics, and the structural invariants
that make cockpit self-contradiction impossible (HAVE ⟹ CAN at construction;
every registry stance covered by a capability claim).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.agent import AGENTS, HOOK_INTENTS, VENDORS, Deploy, Native
from dotfiles.cmd.agent.capability_matrix import CAPABILITY_MATRIX, Cell
from dotfiles.cmd.agent.fleet import (
    CAPABILITY_SURFACES,
    FleetInvariantError,
    _check_invariant,
    build_fleet,
    probe_deploy,
)

# ---------------------------------------------------------------------------
# Probe engine semantics
# ---------------------------------------------------------------------------


def test_probe_exists(tmp_path: Path) -> None:
    target = tmp_path / "file.json"
    spec = Deploy("file.json")
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "missing"
    target.write_text("{}")
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "present"


def test_probe_contains(tmp_path: Path) -> None:
    spec = Deploy("settings.json", proof="contains", needle="statusLine")
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "missing"
    (tmp_path / "settings.json").write_text("{}")
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "empty"
    (tmp_path / "settings.json").write_text('{"statusLine": {}}')
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "present"


def test_probe_md_dir_counts(tmp_path: Path) -> None:
    d = tmp_path / "agents"
    spec = Deploy("agents", proof="md-dir")
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "missing"
    d.mkdir()
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "empty"
    (d / "a.md").write_text("# a")
    (d / "b.md").write_text("# b")
    have = probe_deploy(spec, home=tmp_path, repo=tmp_path)
    assert have.state == "present"
    assert have.count == 2


def test_probe_skill_dirs_counts_subdirs_only(tmp_path: Path) -> None:
    d = tmp_path / "skills"
    d.mkdir()
    (d / "alpha").mkdir()
    (d / "stray.txt").write_text("x")
    have = probe_deploy(Deploy("skills", proof="skill-dirs"), home=tmp_path, repo=tmp_path)
    assert have.state == "present"
    assert have.count == 1


def test_probe_hook_intents_full_partial_empty(tmp_path: Path) -> None:
    cfg = tmp_path / "hooks.json"
    spec = Deploy("hooks.json", proof="hook-intents")
    cfg.write_text("{}")
    assert probe_deploy(spec, home=tmp_path, repo=tmp_path).state == "empty"
    cfg.write_text("guard-sensitive-file.sh")
    have = probe_deploy(spec, home=tmp_path, repo=tmp_path)
    assert have.state == "partial"
    assert have.count == 1
    cfg.write_text(" ".join(script for _i, script in HOOK_INTENTS))
    have = probe_deploy(spec, home=tmp_path, repo=tmp_path)
    assert have.state == "present"
    assert have.count == len(HOOK_INTENTS)


def test_probe_repo_rooted_deploy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    rules = repo / "rules"
    rules.mkdir(parents=True)
    (rules / "shared.mdc").write_text("---")
    have = probe_deploy(
        Deploy("rules", proof="mdc-dir", root="repo"), home=tmp_path / "home", repo=repo
    )
    assert have.state == "present"
    assert have.count == 1


# ---------------------------------------------------------------------------
# Structural invariants — the drift gates
# ---------------------------------------------------------------------------


def test_fleet_covers_every_vendor_and_capability_surface(tmp_path: Path) -> None:
    fleet = build_fleet(home=tmp_path, dotfiles_dir=tmp_path)
    assert {(c.vendor, c.surface) for c in fleet.cells} == {
        (a, s) for a in AGENTS for s in CAPABILITY_SURFACES
    }


def test_deploy_cells_always_carry_a_probe(tmp_path: Path) -> None:
    fleet = build_fleet(home=tmp_path, dotfiles_dir=tmp_path)
    for cell in fleet.cells:
        if cell.stance == "deploy":
            assert cell.have is not None, f"({cell.vendor},{cell.surface}) deploy without probe"
        else:
            assert cell.have is None


def test_have_implies_can_for_the_whole_registry() -> None:
    """The structural invariant: a Deploy/Native stance demands a deployable CAN.

    This subsumes (and is stronger than) the old test_deploy_path_implies_
    capability_support — it covers every capability surface, including
    statusline and permissions, and it's also enforced at runtime by
    build_fleet, so a violating registry can't even render.
    """
    matrix = {cap.key: cap.cells for cap in CAPABILITY_MATRIX}
    for vendor in VENDORS:
        for surface in CAPABILITY_SURFACES:
            stance = vendor.surfaces.stance(surface)
            if isinstance(stance, (Deploy, Native)):
                status = matrix[surface][vendor.name].status
                assert status in ("yes", "beta", "ext"), (
                    f"{vendor.name} deploys {surface!r} but the matrix says {status!r}"
                )


def test_build_fleet_raises_on_can_violation() -> None:
    bad = Cell(status="no", src="https://example.com")
    with pytest.raises(FleetInvariantError, match=r"hermes.*statusline"):
        _check_invariant("hermes", "statusline", bad, Deploy(".hermes/status"))


def test_native_against_unverified_also_raises() -> None:
    with pytest.raises(FleetInvariantError, match="marks native"):
        _check_invariant("hermes", "statusline", Cell(status="unverified"), Native("ships it"))


def test_local_stances_never_probe(tmp_path: Path) -> None:
    fleet = build_fleet(home=tmp_path, dotfiles_dir=tmp_path)
    gem_hooks = fleet.cell("gemini", "hooks")
    assert gem_hooks.stance == "local"
    assert gem_hooks.note
    assert gem_hooks.have is None
