"""Domain models for machine-state snapshots and drift."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrewState(BaseModel):
    """Installed Homebrew top-level packages at capture time."""

    model_config = ConfigDict(frozen=True)

    leaves: tuple[str, ...]
    casks: tuple[str, ...]


class SymlinkState(BaseModel):
    """One managed symlink and where it points at capture time."""

    model_config = ConfigDict(frozen=True)

    path: str
    target: str
    ok: bool


class Snapshot(BaseModel):
    """A point-in-time capture of machine state, persisted as JSON."""

    model_config = ConfigDict(frozen=True)

    taken_at: datetime
    brew: BrewState
    runtimes: dict[str, str]
    symlinks: tuple[SymlinkState, ...]
    agent_config: dict[str, str]


class RuntimeChange(BaseModel):
    """A runtime whose version differs between two snapshots."""

    model_config = ConfigDict(frozen=True)

    name: str
    old: str
    new: str


class SymlinkChange(BaseModel):
    """A managed symlink whose target or ok-state differs between two snapshots."""

    model_config = ConfigDict(frozen=True)

    path: str
    old_target: str
    new_target: str
    broke: bool


class SnapshotDiff(BaseModel):
    """The drift between two snapshots (old -> new)."""

    model_config = ConfigDict(frozen=True)

    brew_added: tuple[str, ...]
    brew_removed: tuple[str, ...]
    runtimes_changed: tuple[RuntimeChange, ...]
    symlinks_changed: tuple[SymlinkChange, ...]
    agent_config_changed: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (
            self.brew_added
            or self.brew_removed
            or self.runtimes_changed
            or self.symlinks_changed
            or self.agent_config_changed
        )
