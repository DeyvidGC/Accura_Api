"""Application configuration settings."""

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration values loaded from environment variables."""

    database_url: str = Field(
        default=(
            "postgresql+psycopg://postgres:postgres@localhost:5432/accura_api"
        ),
        description=(
            "Database connection URL. Defaults to a local PostgreSQL instance"
            " suitable for development."
        ),
    )
    database_pool_size: int = Field(
        default=5,
        ge=1,
        description="Base size of the SQLAlchemy connection pool",
    )
    database_max_overflow: int = Field(
        default=10,
        ge=0,
        description="Maximum number of additional database connections",
    )
    database_pool_timeout: int = Field(
        default=30,
        ge=1,
        description="Seconds to wait when retrieving a connection from the pool",
    )
    database_ssl_mode: str | None = Field(
        default=None,
        description=(
            "Optional PostgreSQL sslmode flag (e.g. 'require' for Azure managed"
            " instances)."
        ),
    )
    secret_key: str = Field(
        default="change_this_secret", description="Secret key for signing JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=60, description="Number of minutes before access tokens expire"
    )
    smtp_host: str | None = Field(
        default=None, description="SMTP host used to send transactional emails"
    )
    smtp_port: int = Field(default=587, description="SMTP port for outgoing email")
    smtp_username: str | None = Field(
        default=None, description="SMTP username for authentication"
    )
    smtp_password: str | None = Field(
        default=None, description="SMTP password for authentication"
    )
    smtp_sender: str | None = Field(
        default=None, description="Sender email address for transactional emails"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()
