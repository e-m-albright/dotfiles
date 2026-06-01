"""Hexagonal ports: the only interfaces the core depends on.

Concrete implementations live in `dotfiles_cli.adapters`; tests inject fakes.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from dotfiles_cli.core.models import CommandResult


@runtime_checkable
class ProcessRunner(Protocol):
    """Runs external commands. The single subprocess seam for the whole app."""

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult: ...


@runtime_checkable
class FileSystem(Protocol):
    """Filesystem reads/writes the core needs (e.g. authorized_keys)."""

    def read_text(self, path: Path) -> str: ...

    def write_text(self, path: Path, content: str) -> None: ...

    def exists(self, path: Path) -> bool: ...

    def mkdir(self, path: Path, *, parents: bool = True) -> None: ...

    def chmod(self, path: Path, mode: int) -> None: ...


@runtime_checkable
class Clock(Protocol):
    """Time source, so time-dependent behavior stays testable.

    Implementations MUST return timezone-aware datetimes in UTC. Callers convert
    to local time only at display edges; the core never handles naive datetimes.
    """

    def now(self) -> datetime: ...
