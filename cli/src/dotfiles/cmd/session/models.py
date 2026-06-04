"""Domain models for zellij sessions and live agent discovery."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

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


class AgentActivity(BaseModel):
    """A recently-active agent session, discovered from transcript file mtimes."""

    model_config = ConfigDict(frozen=True)

    agent: Agent
    cwd: str
    last_active: datetime
