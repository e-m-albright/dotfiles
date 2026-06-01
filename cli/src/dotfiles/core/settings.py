"""Environment-driven configuration (12-factor) via pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOTFILES_", extra="ignore")

    log_level: LogLevel = "WARNING"
    default_session: str = "mobile"


class LlmSettings(BaseSettings):
    """LM Studio bench settings — env var names match llm-bench.sh exactly (no prefix).

    pydantic-settings uppercases field names to match env vars automatically when
    env_prefix="" (e.g. field `lms_host` reads env `LMS_HOST`).
    """

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    lms_host: str = "http://localhost:1234"
    pp_tokens: int = 128
    tg_tokens: int = 256
    load_ctx: int = 32768
