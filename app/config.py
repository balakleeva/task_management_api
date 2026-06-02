
"""
Application configuration module.
Manages environment variables and application settings using Pydantic v2.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses pydantic-settings for automatic .env file loading and validation.
    """
    
    # Application Metadata
    APP_NAME: str = "Task Management API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database Configuration
    DATABASE_URL: str
    DATABASE_URL_SYNC: str  # For Alembic migrations
    
    # Security Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Email Configuration (for password reset)
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None
    
    # Default admin seed (creates admin user on startup if missing)
    SEED_DEFAULT_ADMIN: bool = True
    # In development, reset default admin password from env on each startup
    SEED_DEFAULT_ADMIN_SYNC_PASSWORD: bool = True
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "AdminChangeMe123!"
    DEFAULT_ADMIN_FULL_NAME: str = "Default Admin"

    # Additional admins: comma-separated emails (promote existing users on startup)
    ADMIN_EMAILS: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5

    @property
    def admin_emails_list(self) -> List[str]:
        """Normalized list of admin emails from ADMIN_EMAILS."""
        if not self.ADMIN_EMAILS.strip():
            return []
        return [
            email.strip().lower()
            for email in self.ADMIN_EMAILS.split(",")
            if email.strip()
        ]
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env
    )


# Global settings instance
settings = Settings()