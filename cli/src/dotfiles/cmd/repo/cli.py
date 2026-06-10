"""`dotfiles repo` commands — assert a repo follows the Canon's practices."""

from __future__ import annotations

from itertools import groupby
from pathlib import Path
from typing import Annotated

import typer

from dotfiles.cmd.repo.models import RepoAudit, RepoCheck
from dotfiles.cmd.repo.service import RepoAuditService
from dotfiles.console import console, print_section, print_title

repo_app = typer.Typer(help="Assert repos follow the Canon (gates, docs, stack hygiene).")

_GLYPH: dict[str, str] = {
    "pass": "[green]✓[/]",
    "fail": "[red]✗[/]",
    "warn": "[yellow]⚠[/]",
    "na": "[dim]·[/]",
}
_NAME_W = 12
_GRADE_COLOR = {"A": "green", "A-": "green", "B": "cyan", "C": "yellow", "D": "yellow", "F": "red"}


def _check_line(c: RepoCheck) -> str:
    glyph = _GLYPH.get(c.status, "?")
    line = f"  {glyph} {c.name:<{_NAME_W}}"
    if c.detail:
        line += f" [dim]{c.detail}[/]"
    if c.fix and c.status in ("fail", "warn"):
        line += f"  [yellow]→ {c.fix}[/]"
    return line


def _render_audit(audit: RepoAudit) -> None:
    grade_color = _GRADE_COLOR.get(audit.grade, "dim")
    console.print(
        f"  [dim]{audit.repo_path}[/]\n"
        f"  stack [dim]{audit.stack}[/]   "
        f"grade [{grade_color}]{audit.grade}[/]   "
        f"[dim]{audit.passed}/{len(audit.required)} checks · {audit.failures} failing[/]"
    )
    for category, group in groupby(audit.checks, key=lambda c: c.category):
        print_section(console, category)
        for c in group:
            console.print(_check_line(c))


@repo_app.command("audit")
def audit(
    path: Annotated[
        Path | None, typer.Argument(help="Repo to audit (defaults to the current directory).")
    ] = None,
) -> None:
    """Check a repo against the Canon: gates, docs, and stack hygiene."""
    repo_path = (path or Path.cwd()).resolve()
    print_title(console, "repo", "audit")
    if not repo_path.is_dir():
        console.print(f"  [red]✗[/] not a directory: {repo_path}")
        raise typer.Exit(code=1)
    result = RepoAuditService(repo_path=repo_path).audit()
    _render_audit(result)
    if result.failures:
        raise typer.Exit(code=1)
