# pyright: basic
"""iCloud adapter for Hide My Email — the imperative shell around the pyicloud lib.

Confined to one file in pyright `basic` mode because pyicloud ships no `py.typed`;
in strict mode every call on its objects would be an `Unknown`-type error, and the
repo's `type: ignore` budget is already at its ratchet ceiling. The `MaskProvider`
port and the `create_mask` core stay strict and fully tested. iCloud's own
`HideMyEmailService` already implements the port (`generate` + `reserve`), so login
is all this layer does. Upgrade path: drop the mode line once pyicloud publishes
type hints, then annotate `_login`'s return as `HideMyEmailService`.

pyicloud is imported lazily inside `_login` so the rest of the CLI never pays its
(heavy) import cost, and so non-email commands don't load keyring/srp/cryptography.
"""

from __future__ import annotations

import getpass

from dotfiles.cmd.email.service import MaskError, MaskProvider


def build_icloud_provider(apple_id: str) -> MaskProvider:
    """Log into iCloud and return its Hide My Email service as a `MaskProvider`."""
    return _login(apple_id)


def _login(apple_id: str):
    """Authenticate (keyring password, prompting once if absent) and clear any 2FA gate."""
    from pyicloud import PyiCloudService
    from pyicloud.utils import get_password_from_keyring

    password = get_password_from_keyring(apple_id) or _prompt_and_store_password(apple_id)
    api = PyiCloudService(apple_id, password)
    if api.requires_2fa:
        _complete_2fa(api)
    return api.hidemyemail


def _prompt_and_store_password(apple_id: str) -> str:
    """Prompt for the iCloud password (hidden) and stash it in the system keyring."""
    from pyicloud.utils import store_password_in_keyring

    password = getpass.getpass(f"iCloud password for {apple_id}: ")
    if not password:
        raise MaskError("No iCloud password provided.")
    store_password_in_keyring(apple_id, password)
    return password


def _complete_2fa(api) -> None:
    """Validate an interactive two-factor code and trust this session going forward."""
    code = input("Two-factor code (from a trusted Apple device): ").strip()
    if not api.validate_2fa_code(code):
        raise MaskError("Two-factor verification failed.")
    if not api.is_trusted_session:
        api.trust_session()
