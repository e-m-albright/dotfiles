"""Stats render helpers for `dotfiles agent stats`."""

from __future__ import annotations

from rich.markup import escape
from rich.table import Table

from dotfiles.cmd.agent.skill_stats import SkillStat, SkillUsageReport
from dotfiles.console import console, print_title


def render_stats(report: SkillUsageReport) -> None:
    days = (report.now - report.since).days
    print_title(console, "agent", "stats")
    console.print(
        f"[bold]Skill Usage[/]  [dim]{report.projects} projects · "
        f"{report.total_fires} fires · {report.sessions} sessions · last {days}d[/]"
    )
    _render_leaderboard(report.leaderboard)
    _render_weak_triggers(report.weak_triggers)
    _render_dead(report.dead)
    _render_sequences(report.sequences)
    _render_vendors(report.vendor_counts)
    if report.dropped_lines:
        console.print(f"\n[dim]({report.dropped_lines} unparseable transcript lines skipped)[/]")


def _render_leaderboard(rows: tuple[SkillStat, ...]) -> None:
    console.print()
    console.print("[bold]Leaderboard[/]")
    if not rows:
        console.print("  [dim](no skill invocations in window)[/]")
        return
    tbl = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    tbl.add_column("Skill", style="dim", min_width=28)
    tbl.add_column("fires", justify="right")
    tbl.add_column("auto%", justify="right")
    tbl.add_column("trend")
    tbl.add_column("verdict")
    for s in rows[:15]:
        tbl.add_row(escape(s.skill), str(s.fires), f"{s.auto_pct}%", s.sparkline, s.verdict)
    console.print(tbl)


def _render_weak_triggers(rows: tuple[SkillStat, ...]) -> None:
    if not rows:
        return
    console.print()
    console.print("[bold]⚠ Trigger health[/] [dim]— reached mostly by typing the slash command[/]")
    for s in rows:
        console.print(
            f"  [yellow]{escape(s.skill)}[/]  {s.fires} fires / {s.explicit} explicit"
            "  → tighten its description:"
        )


def _render_dead(dead: tuple[str, ...]) -> None:
    if not dead:
        return
    console.print()
    console.print(
        f"[bold]🪦 Dead[/] [dim]— deployed, 0 fires in window ({len(dead)} candidates)[/]"
    )
    console.print("  [dim]" + " · ".join(escape(d) for d in dead) + "[/]")


def _render_sequences(sequences: tuple[tuple[tuple[str, str], int], ...]) -> None:
    if not sequences:
        return
    console.print()
    console.print("[bold]🔗 Sequences[/] [dim]— skills that chain[/]")
    for (first, second), count in sequences[:8]:
        console.print(f"  [dim]{escape(first)} → {escape(second)}[/]  ({count}x)")


def _render_vendors(counts: tuple[tuple[str, int], ...]) -> None:
    console.print()
    parts = "  ".join(f"{escape(v)} {n}" for v, n in counts) or "[dim](none)[/]"
    console.print(f"[bold]Vendors[/]  {parts}  [dim]· Cursor — (GUI, no logs)[/]")
    if any(v == "codex" for v, _ in counts):
        console.print(
            "  [dim]Codex fires = SKILL.md opens per session"
            " (autonomous; slash-invokes not separable)[/]"
        )


def stats_json(r: SkillUsageReport) -> dict[str, object]:
    return {
        "since": r.since.isoformat(),
        "now": r.now.isoformat(),
        "total_fires": r.total_fires,
        "projects": r.projects,
        "sessions": r.sessions,
        "dropped_lines": r.dropped_lines,
        "leaderboard": [
            {
                "skill": s.skill,
                "fires": s.fires,
                "explicit": s.explicit,
                "auto_pct": s.auto_pct,
                "projects": s.projects,
                "canonical": s.canonical,
                "last_seen": s.last_seen.isoformat(),
                "verdict": s.verdict,
            }
            for s in r.leaderboard
        ],
        "dead": list(r.dead),
        "weak_triggers": [s.skill for s in r.weak_triggers],
        "sequences": [{"from": a, "to": b, "count": n} for (a, b), n in r.sequences],
        "vendors": dict(r.vendor_counts),
    }
