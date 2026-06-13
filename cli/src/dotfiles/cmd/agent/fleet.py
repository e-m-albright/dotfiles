"""The fleet model — one record per (vendor, surface): CAN x STANCE x HAVE.

This is the single source of truth every cockpit view projects from:

- **CAN** — the vendor capability claim + receipt, from ``capability_matrix``.
- **STANCE** — our deploy intent and scope, from the ``VENDORS`` registry
  (``Deploy`` / ``Native`` / ``Local`` / none).
- **HAVE** — the live, probed deployment state. Computed here, by one engine,
  from each Deploy's proof spec. Never asserted, never hand-listed.

``build_fleet`` raises ``FleetInvariantError`` when the registry declares a
Deploy for a capability the matrix says the vendor lacks — HAVE ⟹ CAN is a
construction-time invariant, so the views *cannot* contradict each other about
what is possible vs what we deployed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import (
    HOOK_INTENTS,
    VENDORS,
    Deploy,
    Local,
    Native,
    SurfaceName,
)
from dotfiles.cmd.agent.capability_matrix import CAPABILITY_MATRIX, Cell
from dotfiles.fsutil import list_dir, read_text_or, subdirs

# The surfaces with a capability row (CAN). "settings" is plumbing — no claim.
CAPABILITY_SURFACES: tuple[SurfaceName, ...] = (
    "rules",
    "skills",
    "subagents",
    "mcp",
    "hooks",
    "statusline",
    "permissions",
)

# Capability statuses under which a global deploy is coherent. Deploying against
# "no" (proven absent) or "unverified" (no evidence) is a registry bug.
_DEPLOYABLE: frozenset[str] = frozenset({"yes", "beta", "ext"})

StanceKind = Literal["deploy", "native", "local", "none"]
HaveState = Literal["present", "partial", "empty", "missing"]


class FleetInvariantError(RuntimeError):
    """The registry and the capability matrix contradict each other (HAVE ⟹ CAN broken)."""


class Have(BaseModel):
    """One live-probed deployment state for a Deploy stance."""

    model_config = ConfigDict(frozen=True)

    state: HaveState
    path: str
    count: int | None = None  # items proven (skills, .md files, wired hook intents)


class FleetCell(BaseModel):
    """The one record for (vendor, surface): capability, our stance, live state."""

    model_config = ConfigDict(frozen=True)

    vendor: str
    surface: str
    can: Cell  # the vendor capability claim + its receipt
    stance: StanceKind
    note: str = ""  # Native note / Local reason
    have: Have | None = None  # probed iff stance == "deploy"


class Fleet(BaseModel):
    """All (vendor, surface) cells — every cockpit view is a projection of this."""

    model_config = ConfigDict(frozen=True)

    cells: tuple[FleetCell, ...]

    def cell(self, vendor: str, surface: str) -> FleetCell:
        for c in self.cells:
            if c.vendor == vendor and c.surface == surface:
                return c
        raise KeyError(f"no fleet cell for ({vendor!r}, {surface!r})")

    def vendor_cells(self, vendor: str) -> list[FleetCell]:
        return [c for c in self.cells if c.vendor == vendor]


# ---------------------------------------------------------------------------
# The probe engine — HAVE, computed one way for everyone
# ---------------------------------------------------------------------------


def _dir_count(path: Path, match: Literal["md", "mdc", "subdir"]) -> int | None:
    """Matching entries in *path*, or None when it isn't a directory."""
    if not path.is_dir():
        return None
    if match == "subdir":
        return len(subdirs(path))
    return sum(1 for e in list_dir(path) if not e.is_dir() and e.suffix == f".{match}")


def _from_count(path: Path, count: int | None) -> Have:
    if count is None:
        return Have(state="missing", path=str(path))
    return Have(state="present" if count else "empty", path=str(path), count=count)


def _probe_contains(path: Path, needle: str) -> Have:
    if not path.exists():
        return Have(state="missing", path=str(path))
    state: HaveState = "present" if needle in read_text_or(path) else "empty"
    return Have(state=state, path=str(path))


def _probe_hook_intents(path: Path) -> Have:
    """All shared hook scripts wired in the live config = present; some = partial."""
    if not path.exists():
        return Have(state="missing", path=str(path))
    text = read_text_or(path)
    wired = sum(1 for _intent, script in HOOK_INTENTS if script in text)
    state: HaveState = (
        "present" if wired == len(HOOK_INTENTS) else ("partial" if wired else "empty")
    )
    return Have(state=state, path=str(path), count=wired)


def probe_deploy(deploy: Deploy, *, home: Path, repo: Path) -> Have:
    """Run one Deploy's proof spec against the live filesystem."""
    path = (home if deploy.root == "home" else repo) / deploy.path
    if deploy.proof == "contains":
        return _probe_contains(path, deploy.needle)
    if deploy.proof == "hook-intents":
        return _probe_hook_intents(path)
    if deploy.proof in ("md-dir", "mdc-dir", "skill-dirs"):
        match: Literal["md", "mdc", "subdir"] = (
            "subdir"
            if deploy.proof == "skill-dirs"
            else ("mdc" if deploy.proof == "mdc-dir" else "md")
        )
        return _from_count(path, _dir_count(path, match))
    state: HaveState = "present" if path.exists() else "missing"
    return Have(state=state, path=str(path))


# ---------------------------------------------------------------------------
# Building the fleet
# ---------------------------------------------------------------------------


def _build_cell(
    vendor_name: str, surface: SurfaceName, can: Cell, have: Have | None, stance: object
) -> FleetCell:
    if isinstance(stance, Deploy):
        return FleetCell(vendor=vendor_name, surface=surface, can=can, stance="deploy", have=have)
    if isinstance(stance, Native):
        return FleetCell(
            vendor=vendor_name, surface=surface, can=can, stance="native", note=stance.note
        )
    if isinstance(stance, Local):
        return FleetCell(
            vendor=vendor_name, surface=surface, can=can, stance="local", note=stance.why
        )
    return FleetCell(vendor=vendor_name, surface=surface, can=can, stance="none")


def _check_invariant(vendor_name: str, surface: SurfaceName, can: Cell, stance: object) -> None:
    if isinstance(stance, (Deploy, Native)) and can.status not in _DEPLOYABLE:
        kind = "deploys" if isinstance(stance, Deploy) else "marks native"
        raise FleetInvariantError(
            f"{vendor_name} {kind} {surface!r} but the capability matrix says "
            f"{can.status!r} — reconcile the registry stance or the matrix cell"
        )


def build_fleet(*, home: Path, dotfiles_dir: Path) -> Fleet:
    """Compose CAN (matrix) x STANCE (registry) x HAVE (live probes) for every cell."""
    can_by_key = {cap.key: cap.cells for cap in CAPABILITY_MATRIX}
    cells: list[FleetCell] = []
    for vendor in VENDORS:
        for surface in CAPABILITY_SURFACES:
            can = can_by_key[surface][vendor.name]
            stance = vendor.surfaces.stance(surface)
            _check_invariant(vendor.name, surface, can, stance)
            have = (
                probe_deploy(stance, home=home, repo=dotfiles_dir)
                if isinstance(stance, Deploy)
                else None
            )
            cells.append(_build_cell(vendor.name, surface, can, have, stance))
    return Fleet(cells=tuple(cells))
