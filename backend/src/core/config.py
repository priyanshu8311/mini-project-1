from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url


def sanitize_database_url(url_str: str) -> str:
    """Normalize and sanitize PostgreSQL connection string for asyncpg driver."""
    if not url_str or not isinstance(url_str, str):
        return url_str

    url_str = url_str.strip()

    # Preserve SQLite for local unit test suites
    if url_str.startswith(("sqlite:", "sqlite+")):
        return url_str

    # Convert common legacy/PaaS prefixes to asynchronous asyncpg driver
    if url_str.startswith("postgres://"):
        url_str = "postgresql+asyncpg://" + url_str[len("postgres://"):]
    elif url_str.startswith("postgresql://"):
        url_str = "postgresql+asyncpg://" + url_str[len("postgresql://"):]
    elif url_str.startswith("postgresql+psycopg2://"):
        url_str = "postgresql+asyncpg://" + url_str[len("postgresql+psycopg2://"):]

    url = make_url(url_str)
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+asyncpg")

    # Sanitize query parameters: asyncpg does not accept libpq-specific flags
    query = dict(url.query)
    for libpq_key in ("channel_binding", "gssencmode", "target_session_attrs"):
        query.pop(libpq_key, None)

    # Convert sslmode to ssl for asyncpg
    sslmode = query.pop("sslmode", None)
    if sslmode:
        if sslmode in ("require", "verify-ca", "verify-full", "prefer"):
            query["ssl"] = "require"
        elif sslmode in ("disable",):
            query.pop("ssl", None)

    # Auto-enable SSL for known remote cloud databases if not explicitly set
    host = url.host or ""
    if "ssl" not in query and any(
        cloud_domain in host
        for cloud_domain in ("render.com", "neon.tech", "supabase.co", "amazonaws.com")
    ):
        query["ssl"] = "require"

    url = url._replace(query=query)
    return url.render_as_string(hide_password=False)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Information
    PROJECT_NAME: str = "Smart Inventory Management & Demand Forecasting"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = Field(default=8000, description="Server port, automatically read from Render's $PORT")

    # Security & Authentication
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production-min-32-chars",
        description="High-entropy secret key for JWT signing",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str = Field(
        default="dGVzdF9lbmNyeXB0aW9uX2tleV9mb3JfZGV2XzMyYnl0ZXM=",
        description="Base64 32-byte key for AES-256-GCM symmetric encryption",
    )

    # Webhook Secrets
    SHOPIFY_WEBHOOK_SECRET: str = "dev_shopify_webhook_secret_key"
    SQUARE_WEBHOOK_SECRET: str = "dev_square_webhook_secret_key"

    # Database & Cache
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/smart_inventory",
        description="PostgreSQL async connection string (automatically normalized for asyncpg)",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for queue and cache",
    )

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Any) -> str:
        """Ensure DATABASE_URL is normalized for asyncpg with valid SSL parameters."""
        if isinstance(v, str):
            return sanitize_database_url(v)
        return v

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in a production or staging deployment."""
        return self.ENVIRONMENT.lower() in ("production", "prod", "staging")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Enforce strict secret entropy and prevent default development keys in production."""
        if self.is_production:
            # 1. Enforce DATABASE_URL validity in production (never fall back to SQLite or default localhost)
            if not self.DATABASE_URL:
                raise ValueError(
                    "Production environment detected: DATABASE_URL must be explicitly configured."
                )
            if self.DATABASE_URL.startswith(("sqlite:", "sqlite+")):
                raise ValueError(
                    "Production environment detected: SQLite is not supported in production. "
                    "DATABASE_URL must be a valid PostgreSQL asyncpg connection string."
                )
            if (
                "localhost:5432/smart_inventory" in self.DATABASE_URL
                or "postgres:postgres@localhost" in self.DATABASE_URL
            ):
                raise ValueError(
                    "Production environment detected: DATABASE_URL is pointing to default localhost. "
                    "Please configure a valid PostgreSQL connection string in your Render environment variables."
                )

            # 2. Enforce cryptographic secret entropy
            insecure_jwt = "dev-insecure-secret-key-change-in-production-min-32-chars"
            insecure_enc = "dGVzdF9lbmNyeXB0aW9uX2tleV9mb3JfZGV2XzMyYnl0ZXM="
            if self.JWT_SECRET_KEY == insecure_jwt or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "Production environment detected: JWT_SECRET_KEY must be an explicit, "
                    "high-entropy key with at least 32 characters."
                )
            if self.ENCRYPTION_KEY == insecure_enc or len(self.ENCRYPTION_KEY) < 32:
                raise ValueError(
                    "Production environment detected: ENCRYPTION_KEY must be an explicit, "
                    "secure Base64-encoded 32-byte key."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
