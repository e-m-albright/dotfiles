"""Core logic for `dotfiles email`: the Hide My Email port + the pure orchestration.

The `MaskProvider` port is the seam between this strict, fully-testable core and the
untyped iCloud network adapter in `icloud.py`. iCloud's own `HideMyEmailService`
satisfies the port structurally, so the adapter just logs in and hands it back; tests
inject a fake. Keeping `create_mask` provider-agnostic means the generate→reserve flow
(the only real logic) is unit-tested without touching the network.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from dotfiles.adapters.ports import ProcessRunner


class MaskError(RuntimeError):
    """A Hide My Email alias could not be generated or reserved."""


class ReservedMask(BaseModel):
    """A freshly generated alias, reserved under a user-facing label."""

    model_config = ConfigDict(frozen=True)

    address: str
    label: str
    anonymous_id: str | None = None


@runtime_checkable
class MaskProvider(Protocol):
    """Source of Hide My Email aliases — iCloud in prod, a fake in tests.

    Mirrors the two iCloud calls a generation needs. `reserve` returns the raw
    iCloud result map (``hme``, ``anonymousId``, …); `create_mask` parses it so the
    adapter stays a thin pass-through.
    """

    def generate(self) -> str | None: ...

    def reserve(self, email: str, label: str) -> Mapping[str, object]: ...


def create_mask(provider: MaskProvider, label: str) -> ReservedMask:
    """Generate a new alias and reserve it under *label* (the orchestration core)."""
    address = provider.generate()
    if not address:
        raise MaskError("iCloud declined to generate an address (quota reached, or not iCloud+?).")
    result = provider.reserve(address, label)
    reserved = result.get("hme") or address  # reserve echoes the canonical address
    anon = result.get("anonymousId")
    return ReservedMask(
        address=str(reserved),
        label=label,
        anonymous_id=str(anon) if anon else None,
    )


def copy_to_clipboard(
    runner: ProcessRunner,
    text: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> bool:
    """Copy *text* to the macOS clipboard via pbcopy. Returns False off macOS (no pbcopy)."""
    if which("pbcopy") is None:
        return False
    runner.run(("pbcopy",), stdin=text)
    return True
