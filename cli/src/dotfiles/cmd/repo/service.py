"""`dotfiles repo audit` — assert a repo follows the Canon's practices.

Checks any repo for the gates and conventions the Canon enforces here: a justfile
task runner, lefthook pre-commit/pre-push gates, CI, an AGENTS.md/README, a
.gitignore, plus stack-detected linters and lockfiles. Pure path/text probes over
the target dir — no network, no mutation.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from dotfiles.cmd.repo.models import RepoAudit, RepoCheck, RepoCheckStatus

# Per-stack linter evidence (any present ⇒ linting configured) and lockfiles.
_STACK_MARKERS: dict[str, tuple[str, ...]] = {
    "python": ("pyproject.toml", "setup.py", "requirements.txt"),
    "node": ("package.json",),
    "rust": ("Cargo.toml",),
    "go": ("go.mod",),
}
_LINTER_FILES: dict[str, tuple[str, ...]] = {
    "python": ("ruff.toml", ".ruff.toml"),
    "node": ("biome.json", "biome.jsonc", ".eslintrc", ".eslintrc.json", "eslint.config.js"),
    "rust": ("rustfmt.toml", ".rustfmt.toml", "clippy.toml"),
    "go": (".golangci.yml", ".golangci.yaml", ".golangci.toml"),
}
_LOCKFILES: dict[str, tuple[str, ...]] = {
    "python": ("uv.lock", "poetry.lock", "Pipfile.lock"),
    "node": ("bun.lockb", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"),
    "rust": ("Cargo.lock",),
    "go": ("go.sum",),
}


class RepoAuditService:
    """Produces a RepoAudit for a target repo (pure over the filesystem)."""

    def __init__(self, *, repo_path: Path) -> None:
        self._repo = repo_path

    # ------------------------------------------------------------------
    def audit(self) -> RepoAudit:
        stacks = self._detect_stack()
        checks = (
            self._present(
                "Process", "justfile", ("justfile", "Justfile"), "add a justfile task runner"
            ),
            self._present(
                "Process",
                "lefthook",
                ("lefthook.yml", ".lefthook.yml", "lefthook.yaml", ".lefthook.yaml"),
                "add lefthook for pre-commit/pre-push gates",
            ),
            self._ci_check(),
            self._present(
                "Docs", "README", ("README.md", "README.rst", "README"), "add a README.md"
            ),
            self._present(
                "Docs",
                "AGENTS.md",
                ("AGENTS.md", "CLAUDE.md", "GEMINI.md"),
                "add AGENTS.md agent rules",
            ),
            self._present("Docs", ".gitignore", (".gitignore",), "add a .gitignore"),
            self._linter_check(stacks),
            self._lockfile_check(stacks),
            self._ratchet_check(),
        )
        return RepoAudit(
            repo_path=str(self._repo), stack=", ".join(stacks) or "unknown", checks=checks
        )

    # ------------------------------------------------------------------
    def _detect_stack(self) -> list[str]:
        return [
            stack
            for stack, markers in _STACK_MARKERS.items()
            if any((self._repo / m).exists() for m in markers)
        ]

    def _first_existing(self, names: Iterable[str]) -> str | None:
        for name in names:
            if (self._repo / name).exists():
                return name
        return None

    def _present(
        self, category: str, name: str, candidates: tuple[str, ...], fix: str
    ) -> RepoCheck:
        found = self._first_existing(candidates)
        if found:
            return RepoCheck(category=category, name=name, status="pass", detail=found)
        return RepoCheck(category=category, name=name, status="fail", detail="missing", fix=fix)

    def _ci_check(self) -> RepoCheck:
        workflows = self._repo / ".github" / "workflows"
        files = (
            [f for f in workflows.iterdir() if f.suffix in (".yml", ".yaml")]
            if workflows.is_dir()
            else []
        )
        if files:
            return RepoCheck(
                category="Process", name="CI", status="pass", detail=f"{len(files)} workflow(s)"
            )
        return RepoCheck(
            category="Process",
            name="CI",
            status="fail",
            detail="no workflows",
            fix="add .github/workflows/",
        )

    def _per_stack_check(
        self,
        category: str,
        name: str,
        table: dict[str, tuple[str, ...]],
        stacks: list[str],
        fix: str,
        *,
        missing: RepoCheckStatus,
    ) -> RepoCheck:
        """One check across all detected stacks: pass if every stack has evidence."""
        if not stacks:
            return RepoCheck(category=category, name=name, status="na", detail="no known stack")
        missing_stacks = [s for s in stacks if not self._first_existing(table.get(s, ()))]
        if not missing_stacks:
            return RepoCheck(category=category, name=name, status="pass", detail="configured")
        return RepoCheck(
            category=category,
            name=name,
            status=missing,
            detail=f"missing for {', '.join(missing_stacks)}",
            fix=fix,
        )

    def _linter_check(self, stacks: list[str]) -> RepoCheck:
        if not stacks:
            return RepoCheck(category="Stack", name="linter", status="na", detail="no known stack")
        missing = [s for s in stacks if not self._has_linter(s)]
        if not missing:
            return RepoCheck(category="Stack", name="linter", status="pass", detail="configured")
        return RepoCheck(
            category="Stack",
            name="linter",
            status="fail",
            detail=f"missing for {', '.join(missing)}",
            fix="configure a linter/formatter",
        )

    def _has_linter(self, stack: str) -> bool:
        # Python counts ruff configured inline in pyproject [tool.ruff], too.
        if stack == "python" and self._pyproject_has("[tool.ruff"):
            return True
        return self._first_existing(_LINTER_FILES.get(stack, ())) is not None

    def _lockfile_check(self, stacks: list[str]) -> RepoCheck:
        return self._per_stack_check(
            "Stack", "lockfile", _LOCKFILES, stacks, "commit a dependency lockfile", missing="warn"
        )

    def _pyproject_has(self, needle: str) -> bool:
        path = self._repo / "pyproject.toml"
        try:
            return needle in path.read_text()
        except OSError:
            return False

    def _ratchet_check(self) -> RepoCheck:
        """A convergence ratchet locks code-health gains in. Heuristic: a .converge
        dir, or the justfile referencing a ratchet/converge recipe."""
        if (self._repo / ".converge").is_dir():
            return RepoCheck(category="Stack", name="ratchet", status="pass", detail=".converge/")
        justfile = self._first_existing(("justfile", "Justfile"))
        if justfile:
            try:
                text = (self._repo / justfile).read_text().lower()
            except OSError:
                text = ""
            if "ratchet" in text or "converge" in text:
                return RepoCheck(
                    category="Stack", name="ratchet", status="pass", detail="justfile recipe"
                )
        return RepoCheck(
            category="Stack",
            name="ratchet",
            status="warn",
            detail="none found",
            fix="add a converge ratchet to lock code-health gains",
        )
