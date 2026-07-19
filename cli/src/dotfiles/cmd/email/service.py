"""Core logic for `dotfiles email-mask`: the Hide My Email port + pure orchestration.

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

    Provider-specific records are normalized by the adapter before entering the core.
    """

    def generate(self) -> str | None: ...

    def reserve(self, email: str, label: str) -> ReservedMask: ...

    def __iter__(self) -> Iterator[Mask]: ...

    def delete(self, anonymous_id: str) -> Mapping[str, object]: ...

    def deactivate(self, anonymous_id: str) -> Mapping[str, object]: ...


def create_mask(provider: MaskProvider, label: str) -> ReservedMask:
    """Generate a new alias and reserve it under *label* (the orchestration core)."""
    try:
        address = provider.generate()
    except Exception as exc:
        raise MaskError(f"iCloud address generation failed: {exc}") from exc
    if not address:
        raise MaskError("iCloud declined to generate an address (quota reached, or not iCloud+?).")
    try:
        return provider.reserve(address, label)
    except Exception as exc:
        raise MaskError(f"iCloud address reservation failed: {exc}") from exc


def list_masks(provider: MaskProvider) -> list[Mask]:
    """Return all existing aliases, newest iCloud order preserved."""
    try:
        return list(provider)
    except Exception as exc:
        raise MaskError(f"iCloud alias listing failed: {exc}") from exc


def deactivate_mask(provider: MaskProvider, anonymous_id: str) -> None:
    """Deactivate an alias and normalize provider failures at the boundary."""
    _mutate(provider.deactivate, anonymous_id, operation_name="deactivation")


def delete_mask(provider: MaskProvider, anonymous_id: str) -> None:
    """Delete an alias and normalize provider failures at the boundary."""
    _mutate(provider.delete, anonymous_id, operation_name="deletion")


def _mutate(
    operation: Callable[[str], Mapping[str, object]], anonymous_id: str, *, operation_name: str
) -> None:
    try:
        result = operation(anonymous_id)
    except Exception as exc:
        raise MaskError(f"iCloud alias {operation_name} failed: {exc}") from exc
    if result.get("success") is False or result.get("error"):
        detail = result.get("error") or result.get("message") or "provider rejected the request"
        raise MaskError(f"iCloud alias {operation_name} failed: {detail}")


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
    return runner.run(("pbcopy",), stdin=text).ok
