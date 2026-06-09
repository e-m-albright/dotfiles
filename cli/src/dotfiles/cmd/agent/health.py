"""`dotfiles agent health` — bootstrap a repo's code-health backbone.

Runs the converge scorecard against the *current* repo (CWD), writes a
``docs/health/<scope>/baselines.json`` seeded to current actuals via the ratchet
script, and seeds a ``findings.md`` ledger. Deterministic backbone only — the
graded report and the findings backlog stay with the ``/converge`` engine.

The two shell scripts (``scorecard.sh``, ``ratchet-check.sh``) are the single
source of counting truth; this service orchestrates them rather than
reimplementing their grep logic in Python.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lang_packs import GENERIC, detect_pack
from dotfiles.cmd.agent.models import HealthBootstrap, Hotspot, LanguagePack, Scorecard

# Back-compat alias: the generic multi-language family set. Language-specific
# patterns come from the detected pack (ai/skills/converge/lang/).
SUPPRESSION_PATTERNS: dict[str, str] = GENERIC.suppression_patterns

# Seed high, then let `ratchet-check.sh --update` (monotonic: only lowers) write
# the real ceilings from a scoped recount.
_SEED_CEILING = 99999

_POLICY = (
    "Monotonic ratchet — every ceiling may only DECREASE. Raising one needs an "
    "explicit Ratchet-Bump: commit trailer + reason "
    "(see docs/knowledge/engineering-gates.md §1)."
)


class HealthError(RuntimeError):
    """Bootstrap could not complete (not a git repo, a script failed, bad JSON)."""


def git_root(runner: ProcessRunner) -> Path:
    """Resolve the git toplevel of the current working directory (the target repo)."""
    result = runner.run(("git", "rev-parse", "--show-toplevel"))
    if not result.ok:
        raise HealthError("not inside a git repo")
    return Path(result.stdout.strip())


class HealthService:
    """Bootstraps one ``docs/health/<scope>/`` backbone by driving the scripts."""

    def __init__(self, *, runner: ProcessRunner, scripts_dir: Path) -> None:
        self._runner = runner
        self._scorecard = scripts_dir / "scorecard.sh"
        self._ratchet = scripts_dir / "ratchet-check.sh"
        self._lang_dir = scripts_dir.parent / "lang"

    def bootstrap(
        self,
        *,
        target: Path,
        scope: str,
        today: date,
        files_glob: str | None = None,
        run_from: str | None = None,
        force: bool = False,
    ) -> HealthBootstrap:
        """Score the repo, seed (or keep) baselines.json, seed findings.md.

        The language is detected from marker files (overridable with files_glob /
        run_from); the matching pack supplies the glob and suppression patterns.
        """
        pack = detect_pack(target, self._lang_dir)
        glob = files_glob or pack.files_glob
        rfrom = run_from or pack.run_from

        card = self._scorecard_json(target)
        scope_dir = target / "docs" / "health" / scope
        baselines = scope_dir / "baselines.json"
        findings = scope_dir / "findings.md"

        created = force or not baselines.exists()
        if created:
            scope_dir.mkdir(parents=True, exist_ok=True)
            self._write_baselines(baselines, scope, glob, rfrom, card.loc, today, pack)
            self._ratchet_update(baselines, target / rfrom)
        if not findings.exists():
            findings.parent.mkdir(parents=True, exist_ok=True)
            findings.write_text(_findings_skeleton(scope, today))

        return HealthBootstrap(
            scope=scope,
            target=str(target),
            language=pack.language,
            baselines_path=str(baselines),
            findings_path=str(findings),
            created=created,
            scorecard=card,
            total_suppressions=sum(card.suppressions.values()),
        )

    def _scorecard_json(self, target: Path) -> Scorecard:
        result = self._runner.run((str(self._scorecard), "--json"), cwd=target)
        if not result.ok:
            raise HealthError(result.stderr.strip() or "scorecard.sh failed")
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise HealthError(f"scorecard emitted invalid JSON: {exc}") from exc
        hotspots = tuple(Hotspot(**h) for h in data.get("hotspots", []))
        return Scorecard(
            loc=data["loc"],
            since=data["since"],
            suppressions=data.get("suppressions", {}),
            hotspots=hotspots,
        )

    def _write_baselines(
        self,
        path: Path,
        scope: str,
        files_glob: str,
        run_from: str,
        loc: int,
        today: date,
        pack: LanguagePack,
    ) -> None:
        patterns = pack.suppression_patterns
        doc = {
            "scope": scope,
            "language": pack.language,
            "files_glob": files_glob,
            "run_from": run_from,
            "updated": today.isoformat(),
            "policy": _POLICY,
            "loc_nontest": loc,
            "suppressions": dict.fromkeys(patterns, _SEED_CEILING),
            "suppression_patterns": dict(patterns),
        }
        path.write_text(json.dumps(doc, indent=2) + "\n")

    def _ratchet_update(self, baselines: Path, run_from: Path) -> None:
        result = self._runner.run((str(self._ratchet), str(baselines), "--update"), cwd=run_from)
        if not result.ok:
            raise HealthError(result.stderr.strip() or "ratchet-check --update failed")


def _findings_skeleton(scope: str, today: date) -> str:
    """A blank ledger mirroring the docs/health/<scope>/findings.md layout."""
    return f"""# Code-health findings — `{scope}`

Read this first; write back to it. The `/converge` engine reads the **Tolerated**
and **Open backlog** sections before diagnosing, and appends here after a pass.

Severity legend: `will-drift` (regresses without a gate) · `friction` (slows
change) · `aesthetic` (taste, low urgency).

## Run log

- {today.isoformat()} — backbone bootstrapped by `dotfiles agent health`
  (baselines.json seeded from scorecard + ratchet). No grading yet — run `/converge`.

## Open backlog

_Ranked by churn*complexity. Populated by `/converge`._

## Tolerated

_Decisions kept by design, each with an ADR link (docs/adr/)._

## Dismissed

_Investigated, found not real._
"""
