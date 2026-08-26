from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from dotfiles.cmd.email import icloud
from dotfiles.cmd.email.icloud import ICloudMaskProvider
from dotfiles.cmd.email.service import MaskError


class RawService:
    def __init__(self) -> None:
        self.records = [{"hme": "one@icloud.com", "anonymousId": "id-1", "label": "One"}]
        self.deleted: list[str] = []
        self.deactivated: list[str] = []

    def generate(self) -> str:
        return "new@icloud.com"

    def reserve(self, email: str, label: str) -> dict[str, object]:
        return {"hme": email.upper(), "anonymousId": "new-id", "label": label}

    def __iter__(self) -> Iterator[dict[str, object]]:
        return iter(self.records)

    def delete(self, anonymous_id: str) -> dict[str, object]:
        self.deleted.append(anonymous_id)
        return {"success": True}

    def deactivate(self, anonymous_id: str) -> dict[str, object]:
        self.deactivated.append(anonymous_id)
        return {"success": True}


def test_provider_translates_the_complete_icloud_contract() -> None:
    raw = RawService()
    provider = ICloudMaskProvider(raw)

    assert provider.generate() == "new@icloud.com"
    reserved = provider.reserve("new@icloud.com", "News")
    assert (reserved.address, reserved.label, reserved.anonymous_id) == (
        "NEW@ICLOUD.COM",
        "News",
        "new-id",
    )
    assert [mask.address for mask in provider] == ["one@icloud.com"]
    assert provider.delete("id-1") == {"success": True}
    assert provider.deactivate("id-1") == {"success": True}
    assert raw.deleted == ["id-1"]
    assert raw.deactivated == ["id-1"]


def test_provider_reserve_falls_back_to_requested_address_and_optional_id() -> None:
    service = SimpleNamespace(reserve=lambda _email, _label: {})
    reserved = ICloudMaskProvider(service).reserve("fallback@icloud.com", "Fallback")
    assert reserved.address == "fallback@icloud.com"
    assert reserved.anonymous_id is None


def test_prompt_password_rejects_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icloud.getpass, "getpass", lambda _prompt: "")
    with pytest.raises(MaskError, match="No iCloud password"):
        icloud._prompt_password("me@example.com")


def test_prompt_password_returns_hidden_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icloud.getpass, "getpass", lambda _prompt: "secret")
    assert icloud._prompt_password("me@example.com") == "secret"


def test_complete_2fa_validates_and_trusts_session(monkeypatch: pytest.MonkeyPatch) -> None:
    api = SimpleNamespace(
        is_trusted_session=False,
        validate_2fa_code=lambda code: code == "123456",
        trust_session=lambda: setattr(api, "is_trusted_session", True),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: " 123456 ")

    icloud._complete_2fa(api)

    assert api.is_trusted_session is True


def test_complete_2fa_rejects_invalid_code(monkeypatch: pytest.MonkeyPatch) -> None:
    api = SimpleNamespace(validate_2fa_code=lambda _code: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "bad")
    with pytest.raises(MaskError, match="verification failed"):
        icloud._complete_2fa(api)


def test_login_uses_stored_password_without_rewriting_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    api = SimpleNamespace(requires_2fa=False, hidemyemail=service)
    stored: list[tuple[str, str]] = []
    monkeypatch.setattr("pyicloud.utils.get_password_from_keyring", lambda _apple_id: "stored")
    monkeypatch.setattr(
        "pyicloud.utils.store_password_in_keyring",
        lambda apple_id, password: stored.append((apple_id, password)),
    )
    monkeypatch.setattr("pyicloud.PyiCloudService", lambda apple_id, password: api)

    assert icloud._login("me@example.com") is service
    assert stored == []


def test_login_prompts_completes_2fa_and_caches_only_successful_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    api = SimpleNamespace(requires_2fa=True, hidemyemail=service)
    stored: list[tuple[str, str]] = []
    completed: list[object] = []
    monkeypatch.setattr("pyicloud.utils.get_password_from_keyring", lambda _apple_id: None)
    monkeypatch.setattr(
        "pyicloud.utils.store_password_in_keyring",
        lambda apple_id, password: stored.append((apple_id, password)),
    )
    monkeypatch.setattr(icloud, "_prompt_password", lambda _apple_id: "fresh")
    monkeypatch.setattr(icloud, "_complete_2fa", completed.append)
    monkeypatch.setattr("pyicloud.PyiCloudService", lambda apple_id, password: api)

    assert icloud._login("me@example.com") is service
    assert completed == [api]
    assert stored == [("me@example.com", "fresh")]


def test_login_wraps_provider_failure_without_caching_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyicloud.exceptions import PyiCloudException

    stored: list[tuple[str, str]] = []
    monkeypatch.setattr("pyicloud.utils.get_password_from_keyring", lambda _apple_id: None)
    monkeypatch.setattr(
        "pyicloud.utils.store_password_in_keyring",
        lambda apple_id, password: stored.append((apple_id, password)),
    )
    monkeypatch.setattr(icloud, "_prompt_password", lambda _apple_id: "wrong")

    def fail(_apple_id: str, _password: str) -> object:
        raise PyiCloudException("denied")

    monkeypatch.setattr("pyicloud.PyiCloudService", fail)

    with pytest.raises(MaskError, match=r"iCloud login failed.*denied"):
        icloud._login("me@example.com")
    assert stored == []


def test_build_provider_wraps_logged_in_service(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = RawService()
    monkeypatch.setattr(icloud, "_login", lambda _apple_id: raw)
    provider = icloud.build_icloud_provider("me@example.com")
    assert isinstance(provider, ICloudMaskProvider)
    assert provider.generate() == "new@icloud.com"
