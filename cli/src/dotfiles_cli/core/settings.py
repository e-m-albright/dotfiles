"""Environment-driven configuration (12-factor) via pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOTFILES_", extra="ignore")

    log_level: LogLevel = "WARNING"
    default_session: str = "mobile"
