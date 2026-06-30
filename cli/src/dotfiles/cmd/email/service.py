"""Core logic for `dotfiles email`: the Hide My Email port + the pure orchestration.

The `MaskProvider` port is the seam between this strict, fully-testable core and the
untyped iCloud network adapter in `icloud.py`. iCloud's own `HideMyEmailService`
satisfies the port structurally, so the adapter just logs in and hands it back; tests
inject a fake. Keeping `create_mask` provider-agnostic means the generate→reserve flow
(the only real logic) is unit-tested without touching the network.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator, Mapping
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


class Mask(BaseModel):
    """An existing alias as iCloud lists it. `anonymous_id` is the handle for mutations."""

    model_config = ConfigDict(frozen=True)

    address: str
    label: str
    anonymous_id: str
    active: bool


@runtime_checkable
class MaskProvider(Protocol):
    """Source of Hide My Email aliases — iCloud in prod, a fake in tests.

    Mirrors the iCloud calls each operation needs. The methods return iCloud's raw
    result maps (``hme``, ``anonymousId``, ``isActive``, …); the core functions below
    parse them, so the adapter stays a thin pass-through. iCloud's own
    `HideMyEmailService` satisfies this Protocol structurally.
    """

    def generate(self) -> str | None: ...

    def reserve(self, email: str, label: str) -> Mapping[str, object]: ...

    def __iter__(self) -> Iterator[Mapping[str, object]]: ...

    def delete(self, anonymous_id: str) -> Mapping[str, object]: ...

    def deactivate(self, anonymous_id: str) -> Mapping[str, object]: ...


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


def list_masks(provider: MaskProvider) -> list[Mask]:
    """Return all existing aliases, newest iCloud order preserved."""
    return [_parse_mask(raw) for raw in provider]


def _parse_mask(raw: Mapping[str, object]) -> Mask:
    """Project one iCloud ``hmeEmails`` record onto a Mask (tolerant of missing keys)."""
    return Mask(
        address=str(raw.get("hme", "")),
        label=str(raw.get("label", "")),
        anonymous_id=str(raw.get("anonymousId", "")),
        active=bool(raw.get("isActive", True)),
    )


def find_mask(masks: list[Mask], selector: str) -> Mask:
    """Resolve *selector* (an address or an anonymous id) to exactly one alias."""
    matches = [m for m in masks if selector in (m.address, m.anonymous_id)]
    if not matches:
        raise MaskError(f"No Hide My Email alias matching {selector!r}.")
    if len(matches) > 1:
        raise MaskError(f"{selector!r} matches several aliases — use the anonymous id.")
    return matches[0]


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
