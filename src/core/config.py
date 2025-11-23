from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variables."""

    # Environment type
    APP_ENV: str = "development"

    # Root directory and URLs
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PUBLIC_ROUTES: set[str] = {
        "/",
        "/health",
        "/metrics",
        "/favicon.ico",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/user/register",
        "/api/v1/user/login",
    }
    BACKEND_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # AWS Credentials
    AWS_ACCESS_KEY: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "ap-south-1"
    AWS_BUCKET_NAME: str

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-pro"
    MAX_TOKEN: int = 2000
    TEMPERATURE: float = 0.1

    # Global Variables
    API_PREFIX: str = "/api/v1"
    DEFAULT_PAGE: int = 1
    DEFAULT_PAGE_LIMIT: int = 10
    DEFAULT_OFFSET: int = 0

    # Log settings
    LOG_LEVEL: str = "info"
    LOG_ROTATION: str = "00:00"
    LOG_RETENTION: str = "30 days"

    # Configure the settings based on environment
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        raise TypeError("CORS_ORIGINS must be a string or list of strings")


@lru_cache
def load_settings() -> Settings:
    """
    Load settings based on APP_ENV variable.
    Priority:
    1. System Environment Variables (Docker/OS)
    2. .env.{APP_ENV} file
    3. .env file
    4. Defaults in class
    """
    import os

    app_env = os.getenv("APP_ENV", "development")
    env_file = f".env.{app_env}"

    if not os.path.exists(env_file):
        env_file = ".env"

    return Settings(_env_file=env_file)


# Global settings instance:
settings: Settings = load_settings()
