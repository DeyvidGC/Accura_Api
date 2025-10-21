"""Application configuration settings."""

from functools import lru_cache

try:  # pragma: no cover - compatibility shim for pydantic v1/v2
    from pydantic_settings import BaseSettings  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for pydantic v1
    from pydantic import BaseSettings  # type: ignore

from pydantic import Field


class Settings(BaseSettings):
    """Application configuration values loaded from environment variables."""

    database_url: str = Field(
        default=(
            "postgresql+psycopg2://postgres:deyvid12S%23@localhost:5433/accura_api"
        ),
        description="Database connection URL.",
    )
    secret_key: str = Field(
        default="change_this_secret", description="Secret key for signing JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=60, description="Number of minutes before access tokens expire"
    )
    sendgrid_api_key: str | None = Field(
        default="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",
        description="SendGrid API key used for sending transactional emails via the REST API",
    )
    sendgrid_sender: str | None = Field(
        default="deyvidjosephg@gmail.com",
        description="Email address that will appear as the sender of transactional messages",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()
