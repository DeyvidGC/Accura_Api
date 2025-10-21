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
    smtp_host: str | None = Field(
        default=None, description="SMTP server hostname used for email delivery"
    )
    smtp_port: int = Field(
        default=587, description="SMTP server port used for email delivery"
    )
    smtp_username: str | None = Field(
        default=None, description="Username for authenticating with the SMTP server"
    )
    smtp_password: str | None = Field(
        default=None, description="Password for authenticating with the SMTP server"
    )
    smtp_sender: str | None = Field(
        default=None, description="Email address used as sender for outgoing messages"
    )
    smtp_starttls: bool = Field(
        default=True,
        description="Enable STARTTLS negotiation before sending an email message",
    )
    smtp_timeout: float = Field(
        default=30.0, description="Timeout in seconds for SMTP operations"
    )
    sendgrid_api_key: str | None = Field(
        default=None,
        description="SendGrid API key used for sending transactional emails via the REST API",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()
