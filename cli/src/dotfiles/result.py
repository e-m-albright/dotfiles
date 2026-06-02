"""StepResult — the one action-step type every command returns, rendered by console."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

StepLevel = Literal["success", "info", "warn", "error"]


class StepResult(BaseModel):
    """One reported step of an action (remote, agent setup, brew …).

    The single step-result type for the whole app, rendered by ``console.render_steps``.
    *details* is optional supplementary text shown dimmed after the message.
    """

    model_config = ConfigDict(frozen=True)

    level: StepLevel
    message: str
    details: str = ""

    @property
    def ok(self) -> bool:
        """True unless this step is an error — the success/fail view used by setup steps."""
        return self.level != "error"
