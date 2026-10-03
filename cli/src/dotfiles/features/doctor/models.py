"""Domain models for `dotfiles doctor`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

CheckStatus = Literal["ok", "missing", "warn", "fixed"]


class CheckResult(BaseModel):
    """One row of `dotfiles doctor` output."""

    model_config = ConfigDict(frozen=True)

    section: str
    name: str
    status: CheckStatus
    detail: str = ""
    hint: str = ""

    @property
    def is_failure(self) -> bool:
        return self.status == "missing"
