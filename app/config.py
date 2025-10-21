"""Application configuration settings."""

from __future__ import annotations

from functools import lru_cache

ENV_FILE = ".env"
ENV_FILE_ENCODING = "utf-8"

try:  # pragma: no cover - compatibility shim for pydantic v1/v2
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for pydantic v1
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = None  # type: ignore[assignment]

from pydantic import Field

try:  # pragma: no cover - pydantic v2
    from pydantic import model_validator
except ImportError:  # pragma: no cover - pydantic v1
    model_validator = None  # type: ignore[assignment]
    from pydantic import root_validator
else:  # pragma: no cover - pydantic v2
    root_validator = None  # type: ignore[assignment]


class Settings(BaseSettings):
    """Application configuration values loaded from environment variables."""

    if SettingsConfigDict is not None:  # pragma: no branch - simple compatibility shim
        model_config = SettingsConfigDict(  # type: ignore[misc]
            env_file=ENV_FILE, env_file_encoding=ENV_FILE_ENCODING
        )

    database_url: str = Field(
        description="Database connection URL used by SQLAlchemy to connect to the DB",
        min_length=1,
    )
    secret_key: str = Field(
        description="Secret key for signing JWT tokens", min_length=1
    )
    access_token_expire_minutes: int = Field(
        description="Number of minutes before access tokens expire",
        gt=0,
    )
    sendgrid_api_key: str | None = Field(
        default=None,
        description="SendGrid API key used for sending transactional emails via the REST API",
    )
    sendgrid_sender: str | None = Field(
        default=None,
        description="Email address that will appear as the sender of transactional messages",
        min_length=3,
    )

    if model_validator is not None:

        @model_validator(mode="after")  # type: ignore[misc]
        def _validate_sendgrid_pair(self: "Settings") -> "Settings":
            if bool(self.sendgrid_api_key) ^ bool(self.sendgrid_sender):
                raise ValueError(
                    "SENDGRID_API_KEY and SENDGRID_SENDER must both be provided to enable email"
                )
            if self.sendgrid_sender and "@" not in self.sendgrid_sender:
                raise ValueError("SENDGRID_SENDER must be a valid email address")
            return self

    else:

        @root_validator  # type: ignore[misc]
        def _validate_sendgrid_pair(cls, values: dict[str, object]) -> dict[str, object]:
            api_key = values.get("sendgrid_api_key")
            sender = values.get("sendgrid_sender")
            if bool(api_key) ^ bool(sender):
                raise ValueError(
                    "SENDGRID_API_KEY and SENDGRID_SENDER must both be provided to enable email"
                )
            if sender and "@" not in str(sender):
                raise ValueError("SENDGRID_SENDER must be a valid email address")
            return values

    class Config:
        env_file = ENV_FILE
        env_file_encoding = ENV_FILE_ENCODING


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()


def reset_settings_cache() -> None:
    """Clear the settings cache to force reloading from the environment."""

    get_settings.cache_clear()


__all__ = ["Settings", "get_settings", "reset_settings_cache"]
