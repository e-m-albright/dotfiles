import pytest

from dotfiles.settings import Settings


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("DOTFILES_LOG_LEVEL", "DOTFILES_DEFAULT_SESSION"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings()
    assert settings.log_level == "WARNING"
    assert settings.default_session == "mobile"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOTFILES_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DOTFILES_DEFAULT_SESSION", "work")
    settings = Settings()
    assert settings.log_level == "DEBUG"
    assert settings.default_session == "work"


def test_log_level_is_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    import pydantic

    monkeypatch.setenv("DOTFILES_LOG_LEVEL", "NOPE")
    with pytest.raises(pydantic.ValidationError):
        Settings()
