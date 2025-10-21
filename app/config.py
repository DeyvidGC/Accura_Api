"""Application configuration settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = ".env"
ENV_FILE_ENCODING = "utf-8"
DEFAULT_SQLITE_URL = "sqlite:///./accura.db"


class Settings(BaseSettings):
    """Application configuration values loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding=ENV_FILE_ENCODING,
        extra="ignore",
    )

    database_url: str = Field(
        default=DEFAULT_SQLITE_URL,
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

    @model_validator(mode="after")
    def _validate_sendgrid_pair(self) -> "Settings":
        if bool(self.sendgrid_api_key) ^ bool(self.sendgrid_sender):
            raise ValueError(
                "SENDGRID_API_KEY and SENDGRID_SENDER must both be provided to enable email"
            )
        if self.sendgrid_sender and "@" not in self.sendgrid_sender:
            raise ValueError("SENDGRID_SENDER must be a valid email address")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()


def reset_settings_cache() -> None:
    """Clear the settings cache to force reloading from the environment."""

    get_settings.cache_clear()


__all__ = ["Settings", "get_settings", "reset_settings_cache"]
