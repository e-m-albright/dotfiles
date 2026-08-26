import pytest

from dotfiles.settings import Settings


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOTFILES_DEFAULT_SESSION", raising=False)
    settings = Settings()
    assert settings.default_session == "mobile"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOTFILES_DEFAULT_SESSION", "work")
    settings = Settings()
    assert settings.default_session == "work"
