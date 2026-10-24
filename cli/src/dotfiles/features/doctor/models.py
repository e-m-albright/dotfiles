"""Domain models for `dotfiles doctor`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class InferencePool(BaseModel):
    model_config = ConfigDict(strict=True)
    model_count: int


class InferenceHealth(BaseModel):
    """The bounded subset of oMLX health used by host diagnostics."""

    model_config = ConfigDict(strict=True)
    status: str
    engine_pool: InferencePool

    @property
    def ready(self) -> bool:
        return self.status == "healthy" and self.engine_pool.model_count > 0


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
