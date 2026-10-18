from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Information
    PROJECT_NAME: str = "Smart Inventory Management & Demand Forecasting"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

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
        description="PostgreSQL async connection string",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for queue and cache",
    )

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

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
