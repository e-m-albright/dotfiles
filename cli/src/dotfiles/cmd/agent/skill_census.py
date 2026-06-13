"""One skill count to rule them all.

Every view that says anything about deployed skills (Skills & Rules matrix,
``agent verify`` counts, the per-vendor pages) reads this census, so the numbers
cannot disagree. A deployed skill dir is classified against the keep-sets:

- **ours** — one of the canonical ``ai/skills`` set (what ``agent setup`` deploys).
- **external** — intentionally tracked third-party (``external-skills.txt``).
- **foreign** — anything else (vendor-bundled or unknown installs). Reported,
  never counted as ours, never called drift.

Real drift is exactly ``ours < expected`` — canonical skills missing from a
vendor's dir. Extra external/foreign skills are labeled, not alarmed on.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import Vendor
from dotfiles.cmd.agent.skill_prune import canonical_skill_names, external_skill_names
from dotfiles.fsutil import subdirs


class SkillCensus(BaseModel):
    """Deployed-skill counts for one vendor, classified against the keep-sets."""

    model_config = ConfigDict(frozen=True)

    vendor: str
    ours: int  # deployed ∩ canonical
    external: int  # deployed ∩ tracked external
    foreign: int  # deployed but neither (vendor-bundled / unknown)
    expected: int  # the canonical count every skills vendor should carry

    @property
    def deployed(self) -> int:
        return self.ours + self.external + self.foreign

    @property
    def missing(self) -> int:
        """Canonical skills absent from this vendor's dir — the only real drift."""
        return self.expected - self.ours

    def label(self) -> str:
        """Compact display: ours+tracked, with foreign noise annotated, e.g. ``45+17``."""
        intentional = self.ours + self.external
        return f"{intentional}+{self.foreign}" if self.foreign else str(intentional)


def skill_census(vendor: Vendor, *, home: Path, dotfiles_dir: Path) -> SkillCensus | None:
    """Classify *vendor*'s deployed skill dirs, or None when it has no skills deploy."""
    deploy = vendor.deploy("skills")
    if deploy is None:
        return None
    canonical = canonical_skill_names(dotfiles_dir)
    external = external_skill_names(dotfiles_dir)
    root = (home if deploy.root == "home" else dotfiles_dir) / deploy.path
    deployed: set[str] = {p.name for p in subdirs(root)}
    ours = len(deployed & canonical)
    tracked = len(deployed & (external - canonical))
    return SkillCensus(
        vendor=vendor.name,
        ours=ours,
        external=tracked,
        foreign=len(deployed) - ours - tracked,
        expected=len(canonical),
    )
