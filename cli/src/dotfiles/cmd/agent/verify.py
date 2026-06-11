"""Per-vendor surface pages — a projection of the fleet model.

One row per (vendor, surface), all eight surfaces in the same order for every
vendor, so you can read down any vendor and see exactly what it has, what it
lacks, and *why* a surface is intentionally absent (the Local reason renders
instead of a bare n/a). All states come from ``build_fleet``'s live probes —
this module computes nothing of its own.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles.agent import VENDORS, SurfaceName, Vendor
from dotfiles.cmd.agent.fleet import Fleet, FleetCell, Have, probe_deploy
from dotfiles.cmd.agent.models import AgentSurface, AgentSurfaceStatus
from dotfiles.cmd.agent.skill_census import SkillCensus, skill_census

# Every page shows the same rows in the same order: the 7 capability surfaces
# plus the settings plumbing row.
_SURFACE_ORDER: tuple[SurfaceName, ...] = (
    "rules",
    "skills",
    "subagents",
    "mcp",
    "hooks",
    "statusline",
    "permissions",
    "settings",
)

# Deployment-count units per surface (what Have.count counts there).
_COUNT_UNIT: dict[str, str] = {
    "skills": "skills",
    "subagents": "agents",
    "rules": ".mdc",
    "hooks": "hooks wired",
}

_HAVE_STATUS: dict[str, AgentSurfaceStatus] = {
    "present": "present",
    "partial": "empty",  # glyph ○ — the quantity carries the n/N truth
    "empty": "empty",
    "missing": "missing",
}


def _quantity(surface: str, have: Have, census: SkillCensus | None) -> str:
    if surface == "skills" and census is not None and census.deployed > 0:
        # The census label (e.g. "36+18"), so this page and the Skills & Rules
        # matrix show the same notation for the same fact.
        return f"{census.label()} skills"
    unit = _COUNT_UNIT.get(surface)
    if have.count is None or unit is None:
        return ""
    return f"{have.count} {unit}"


def _deployed_surface(vendor: Vendor, cell: FleetCell, census: SkillCensus | None) -> AgentSurface:
    have = cell.have
    if have is None:  # stance=="deploy" always probes; guard for the type-checker
        raise ValueError(f"deploy cell ({vendor.name}, {cell.surface}) without a probe")
    return AgentSurface(
        agent=vendor.name,
        label=cell.surface,
        status=_HAVE_STATUS[have.state],
        detail=have.path,
        quantity=_quantity(cell.surface, have, census),
        path=have.path,
    )


def _undeployed_surface(vendor: Vendor, cell: FleetCell) -> AgentSurface:
    """native → present with its note; local → n/a with its reason; none → bare n/a."""
    if cell.stance == "native":
        return AgentSurface(
            agent=vendor.name,
            label=cell.surface,
            status="present",
            detail=cell.note,
            quantity="native",
        )
    quantity = "local-only" if cell.stance == "local" else "n/a"
    return AgentSurface(
        agent=vendor.name,
        label=cell.surface,
        status="skipped",
        detail=cell.note,
        quantity=quantity,
    )


def _settings_surface(vendor: Vendor, *, home: Path, dotfiles_dir: Path) -> AgentSurface:
    """The settings plumbing row (no capability claim, so it's not a fleet cell)."""
    deploy = vendor.deploy("settings")
    if deploy is None:
        return AgentSurface(agent=vendor.name, label="settings", status="skipped", quantity="n/a")
    have = probe_deploy(deploy, home=home, repo=dotfiles_dir)
    return AgentSurface(
        agent=vendor.name,
        label="settings",
        status=_HAVE_STATUS[have.state],
        detail=have.path,
        path=have.path,
    )


def vendor_surfaces(fleet: Fleet, *, home: Path, dotfiles_dir: Path) -> list[AgentSurface]:
    """The uniform per-vendor checklist — same rows, same order, fleet-derived."""
    results: list[AgentSurface] = []
    for vendor in VENDORS:
        census = skill_census(vendor, home=home, dotfiles_dir=dotfiles_dir)
        for surface in _SURFACE_ORDER:
            if surface == "settings":
                results.append(_settings_surface(vendor, home=home, dotfiles_dir=dotfiles_dir))
            else:
                cell = fleet.cell(vendor.name, surface)
                results.append(
                    _deployed_surface(vendor, cell, census)
                    if cell.stance == "deploy"
                    else _undeployed_surface(vendor, cell)
                )
    return results
