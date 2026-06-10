"""Domain models for `dotfiles repo audit` — Canon conformance for any repo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# pass = present/correct · fail = a required Canon gate is missing ·
# warn = a recommended practice is missing · na = not applicable to this stack.
RepoCheckStatus = Literal["pass", "fail", "warn", "na"]


class RepoCheck(BaseModel):
    """One conformance check against the Canon."""

    model_config = ConfigDict(frozen=True)

    category: str  # grouping (Process · Docs · Stack)
    name: str
    status: RepoCheckStatus
    detail: str = ""  # what was found (or not)
    fix: str = ""  # a one-line hint to close the gap

    @property
    def is_failure(self) -> bool:
        return self.status == "fail"


class RepoAudit(BaseModel):
    """The full conformance report for a repo."""

    model_config = ConfigDict(frozen=True)

    repo_path: str
    stack: str  # detected stack(s), e.g. "python", "node, rust", or "unknown"
    checks: tuple[RepoCheck, ...]

    @property
    def required(self) -> tuple[RepoCheck, ...]:
        """Checks that count toward the grade (everything that isn't n/a)."""
        return tuple(c for c in self.checks if c.status != "na")

    @property
    def passed(self) -> int:
        return sum(1 for c in self.required if c.status == "pass")

    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    @property
    def grade(self) -> str:
        """Letter grade from the pass ratio over gradeable checks (warn = half)."""
        gradeable = self.required
        if not gradeable:
            return "—"
        score = sum(
            1.0 if c.status == "pass" else 0.5 if c.status == "warn" else 0.0 for c in gradeable
        )
        ratio = score / len(gradeable)
        for threshold, letter in ((0.97, "A"), (0.9, "A-"), (0.8, "B"), (0.7, "C"), (0.6, "D")):
            if ratio >= threshold:
                return letter
        return "F"
