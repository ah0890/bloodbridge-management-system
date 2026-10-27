"""Application configuration loaded from environment variables / .env."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BB_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./bloodbridge.db"

    # Secret used to sign session tokens. Must be overridden outside development.
    secret_key: str = Field(default="dev-only-insecure-secret-change-me", min_length=16)
    session_minutes: int = 8 * 60
    cookie_secure: bool = False
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Expose /docs and /openapi.json. Defaults to off in production.
    expose_docs: bool | None = None

    # Login throttling (per username + client IP, in-process).
    login_max_attempts: int = 5
    login_window_seconds: int = 300

    # Operational thresholds (configurable, used consistently across pages).
    low_stock_units: int = 10
    expiry_warning_days: int = 7
    availability_fresh_days: int = 90
    whole_blood_deferral_days: int = 90

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip().startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def docs_enabled(self) -> bool:
        if self.expose_docs is not None:
            return self.expose_docs
        return self.environment != "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "production" and settings.secret_key.startswith("dev-only"):
        raise RuntimeError("BB_SECRET_KEY must be set to a strong random value in production.")
    return settings
