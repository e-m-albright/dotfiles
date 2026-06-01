"""Hexagonal ports: the only interfaces the core depends on.

Concrete implementations live in `dotfiles.adapters`; tests inject fakes.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from dotfiles.core.models import CommandResult

# Alias for unstructured external JSON data (LM Studio API responses).
JsonDict = dict[str, Any]


@runtime_checkable
class ProcessRunner(Protocol):
    """Runs external commands. The single subprocess seam for the whole app."""

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = False,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
    ) -> CommandResult: ...


@runtime_checkable
class HttpClient(Protocol):
    """HTTP client port — mockable seam for LM Studio API calls."""

    def get_json(self, url: str) -> JsonDict: ...

    def post_json(self, url: str, body: JsonDict) -> JsonDict: ...
