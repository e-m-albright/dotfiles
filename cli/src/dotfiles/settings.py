"""Environment-driven configuration (12-factor) via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOTFILES_", extra="ignore")

    default_session: str = "mobile"
    apple_id: str = ""  # iCloud account for `dotfiles email-mask`; set via DOTFILES_APPLE_ID
