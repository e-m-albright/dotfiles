"""Domain models for zellij sessions and live agent discovery."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from dotfiles.agent import Agent


class Session(BaseModel):
    """A zellij session as reported by `zellij list-sessions`."""

    model_config = ConfigDict(frozen=True)

    name: str
    running: bool
    current: bool
    # Age since creation, parsed from zellij's "[Created ... ago]" clause. None
    # when zellij omits it. Used as the staleness signal for pruning exited ones.
    created_age_seconds: int | None = None

    @model_validator(mode="after")
    def current_is_running(self) -> Self:
        if self.current and not self.running:
            raise ValueError("the current session must be running")
        return self


class AgentActivity(BaseModel):
    """A live agent process and the zellij session it runs in.

    `session` is the agent process's inherited ZELLIJ_SESSION_NAME — the exact
    session it lives in — or None when it's running outside any zellij session.
    `cwd` is its working directory, used only to label "elsewhere" agents.
    """

    model_config = ConfigDict(frozen=True)

    agent: Agent
    session: str | None = None
    cwd: str = ""
