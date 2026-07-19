# pyright: basic
"""iCloud adapter for Hide My Email — the imperative shell around the pyicloud lib.

Confined to one file in pyright `basic` mode because pyicloud ships no `py.typed`;
in strict mode every call on its objects would be an `Unknown`-type error, and the
repo's `type: ignore` budget is already at its ratchet ceiling. The `MaskProvider`
port and the `create_mask` core stay strict and fully tested. iCloud's own
`HideMyEmailService` already implements the port (`generate` + `reserve` + iter +
delete + deactivate), so login is all this layer does. Upgrade path: drop the mode
line once pyicloud publishes type hints, then annotate `_login`'s return.

pyicloud is imported lazily inside `_login` so the rest of the CLI never pays its
(heavy) import cost, and so non-email commands don't load keyring/srp/cryptography.
"""

from __future__ import annotations

import getpass
from collections.abc import Iterator, Mapping

from dotfiles.cmd.email.service import Mask, MaskError, MaskProvider, ReservedMask


class ICloudMaskProvider:
    """Translate pyicloud's raw field names into the local mask model."""

    def __init__(self, service) -> None:
        self._service = service

    def generate(self) -> str | None:
        return self._service.generate()

    def reserve(self, email: str, label: str) -> ReservedMask:
        raw = self._service.reserve(email, label)
        anonymous_id = raw.get("anonymousId")
        return ReservedMask(
            address=str(raw.get("hme") or email),
            label=label,
            anonymous_id=str(anonymous_id) if anonymous_id else None,
        )

    def __iter__(self) -> Iterator[Mask]:
        return (parse_icloud_mask(raw) for raw in self._service)

    def delete(self, anonymous_id: str) -> Mapping[str, object]:
        return self._service.delete(anonymous_id)

    def deactivate(self, anonymous_id: str) -> Mapping[str, object]:
        return self._service.deactivate(anonymous_id)


def parse_icloud_mask(raw: Mapping[str, object]) -> Mask:
    """Parse one provider record, rejecting aliases that cannot be addressed safely."""
    address = raw.get("hme")
    anonymous_id = raw.get("anonymousId")
    active = raw.get("isActive", True)
    if not isinstance(address, str) or not address:
        raise ValueError("alias address is missing")
    if not isinstance(anonymous_id, str) or not anonymous_id:
        raise ValueError("alias id is missing")
    if not isinstance(active, bool):
        raise ValueError("alias active state is not a boolean")
    return Mask(
        address=address,
        label=str(raw.get("label", "")),
        anonymous_id=anonymous_id,
        active=active,
    )


def build_icloud_provider(apple_id: str) -> MaskProvider:
    """Log into iCloud and return its Hide My Email service as a `MaskProvider`."""
    return ICloudMaskProvider(_login(apple_id))


def _login(apple_id: str):
    """Authenticate (keyring or prompt), clear any 2FA gate, return the HME service.

    The password is written to the keyring only *after* a login actually succeeds, so a
    mistyped password (or wrong Apple ID) can't poison later runs. Any pyicloud failure
    becomes a MaskError so the CLI prints a clean reason instead of a traceback.
    """
    from pyicloud import PyiCloudService
    from pyicloud.exceptions import PyiCloudException
    from pyicloud.utils import get_password_from_keyring, store_password_in_keyring

    stored = get_password_from_keyring(apple_id)
    password = stored or _prompt_password(apple_id)
    try:
        api = PyiCloudService(apple_id, password)
        if api.requires_2fa:
            _complete_2fa(api)
        service = api.hidemyemail
    except PyiCloudException as exc:
        raise MaskError(f"iCloud login failed for {apple_id}: {exc}") from exc
    if stored is None:
        store_password_in_keyring(apple_id, password)  # cache only a password that worked
    return service


def _prompt_password(apple_id: str) -> str:
    """Prompt (hidden) for the iCloud password; not stored until login succeeds."""
    password = getpass.getpass(f"iCloud password for {apple_id}: ")
    if not password:
        raise MaskError("No iCloud password provided.")
    return password


def _complete_2fa(api) -> None:
    """Validate an interactive two-factor code and trust this session going forward."""
    code = input("Two-factor code (from a trusted Apple device): ").strip()
    if not api.validate_2fa_code(code):
        raise MaskError("Two-factor verification failed.")
    if not api.is_trusted_session:
        api.trust_session()
