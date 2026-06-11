"""Skills render helpers for `dotfiles agent skills`."""

from __future__ import annotations

from rich.markup import escape

from dotfiles.cmd.agent.render.overview import GOLD
from dotfiles.cmd.agent.skill_collision import SkillCollision, SkillCollisionReport
from dotfiles.cmd.agent.skill_inventory import SkillInfo
from dotfiles.cmd.agent.skill_prune import SkillOrphan
from dotfiles.console import console, print_section, print_status

ORIGIN_STYLE: dict[str, str] = {
    "canonical": "green",
    "external": "cyan",
    "plugin": "magenta",
    "builtin": "blue",
    "retired": "red",
    "untracked": "yellow",
}

# Per-origin provenance + how-to-manage hint, shown in each section header so the
# row list needs no origin column. Plugins override this with their marketplace ref.
_ORIGIN_PROVENANCE: dict[str, str] = {
    "canonical": "this repo, ai/skills/ — edit directly",
    "external": "opt-in via external-skills.txt — npx skills add/remove",
    "plugin": "Claude Code plugin — manage via /plugin",
    "builtin": "vendor builtin (Cursor/Codex) — left untouched",
    "retired": "was ours, removed from canonical — dfs agent skills prune",
    "untracked": "manual/registry install — add to external-skills.txt or delete",
}

# (origin, glyph-color, glyph, section hint) — the order they render in.
_ORPHAN_BUCKETS: tuple[tuple[str, str, str, str], ...] = (
    ("retired", "red", "✗", "were ours, renamed/removed — safe to delete"),
    ("builtin", "blue", "·", "shipped by the vendor (Cursor/Codex) — left untouched"),
    ("untracked", "yellow", "?", "registry/manual installs — add to external-skills.txt to keep"),
)


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(1, width - 1)] + "…"


def order_by_origin(skills: list[SkillInfo]) -> list[SkillInfo]:
    """Group by origin (canonical → … → untracked, the ORIGIN_STYLE order), then
    alphabetically by name within each origin. Unknown origins sort last."""
    rank = {origin: i for i, origin in enumerate(ORIGIN_STYLE)}
    return sorted(skills, key=lambda s: (rank.get(s.origin, len(rank)), s.name))


def origin_provenance(origin: str, group: list[SkillInfo]) -> str:
    """Provenance + management hint for an origin's section header. For plugins the
    marketplace ref is the real fingerprint, so surface the distinct ref(s)."""
    if origin == "plugin":
        refs = sorted({s.source for s in group if s.source})
        if refs:
            return f"{', '.join(refs)} — manage via /plugin"
    return _ORIGIN_PROVENANCE.get(origin, "unknown provenance")


def render_skills(skills: list[SkillInfo]) -> None:
    # Per-origin sections (input is already grouped by order_by_origin). The header
    # carries origin + provenance + count, so rows drop the now-redundant origin
    # column and hand that width to the description. Manual columns (not a Rich
    # Table) so a no-wrap description can't collapse the name column at narrow widths.
    name_w = min(34, max((len(s.name) for s in skills), default=8) + 1)
    desc_w = max(16, console.width - 5 - name_w)
    by_origin: dict[str, list[SkillInfo]] = {}
    for s in skills:
        by_origin.setdefault(s.origin, []).append(s)
    for origin, group in by_origin.items():
        color = ORIGIN_STYLE.get(origin, "dim")
        console.print(
            f"\n  [bold {color}]{origin}[/] "
            f"[dim]· {escape(origin_provenance(origin, group))} · {len(group)}[/]"
        )
        for s in group:
            desc = _clip(" ".join(s.description.split()), desc_w)
            console.print(
                f"    {escape(_clip(s.name, name_w).ljust(name_w))} [{GOLD}]{escape(desc)}[/]"
            )


def render_orphans(orphans: list[SkillOrphan]) -> None:
    """Show retired / builtin / untracked orphans in labelled buckets."""
    for origin, color, glyph, hint in _ORPHAN_BUCKETS:
        group = [o for o in orphans if o.origin == origin]
        if not group:
            continue
        print_section(console, origin.capitalize(), hint)
        for o in group:
            console.print(f"  [{color}]{glyph}[/] [dim]{o.location}/[/]{o.name}")


def render_collision_report(report: SkillCollisionReport) -> None:
    console.print(
        f"  [dim]{report.local_count} canonical skills · "
        f"{report.external_count} Pi-package skills scanned[/]"
    )
    if not report.collisions:
        print_status(console, "success", "No local/Pi-package skill collisions found")
        return
    by_domain: dict[str, list[SkillCollision]] = {}
    for collision in report.collisions:
        by_domain.setdefault(collision.domain, []).append(collision)
    for domain in sorted(by_domain):
        print_section(console, domain, "likely overlapping trigger/domain")
        for c in by_domain[domain]:
            glyph = "=" if c.kind == "same-name" else "~"
            console.print(
                f"  [yellow]{glyph}[/] [bold]{escape(c.local.name)}[/] "
                f"[dim]({escape(c.local.path)})[/]  ↔  "
                f"[{GOLD}]{escape(c.external.name)}[/] "
                f"[dim]({escape(c.external.source)} · {escape(c.external.path)})[/]"
            )
            console.print(f"      [dim]{escape(c.reason)}[/]")
