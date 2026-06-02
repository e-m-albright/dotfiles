"""Domain models for zellij sessions and live agent discovery."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from dotfiles.vendor import Vendor


class Session(BaseModel):
    """A zellij session as reported by `zellij list-sessions`."""

    model_config = ConfigDict(frozen=True)

    name: str
    running: bool
    current: bool


class AgentActivity(BaseModel):
    """A recently-active agent session, discovered from transcript file mtimes."""

    model_config = ConfigDict(frozen=True)

    vendor: Vendor
    cwd: str
    last_active: datetime
