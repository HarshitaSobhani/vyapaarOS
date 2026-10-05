from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    environment: Literal["development", "production", "test"] = "development"
    database_url: str = "postgresql+psycopg://vyapaaros:vyapaaros@localhost:5432/vyapaaros"

    secret_key: str = DEV_JWT_SECRET
    jwt_expire_minutes: int = 60 * 12

    demo_user_email: str = "demo@vyapaaros.in"
    demo_user_password: str = ""

    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    default_gst_rate: float = 18.0
    max_upload_bytes: int = 2 * 1024 * 1024
    max_import_rows: int = 5000
    cors_origins: str = ""  # comma-separated; empty means "local frontend only" outside production

    @field_validator("database_url")
    @classmethod
    def _adapt_url(cls, v: str) -> str:
        """Railway supplies postgres:// or postgresql://; SQLAlchemy needs the psycopg driver."""
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        if not origins and self.environment != "production":
            return ["http://localhost:3000"]
        return origins

    def validate_for_runtime(self) -> None:
        if self.environment == "production" and self.secret_key == DEV_JWT_SECRET:
            raise RuntimeError("SECRET_KEY must be set in production")
        if self.environment == "production":
            if any(h in self.database_url for h in ("@localhost", "@127.0.0.1")):
                raise RuntimeError("DATABASE_URL must point at the production database, not localhost")
            if not self.cors_origin_list:
                raise RuntimeError("CORS_ORIGINS must list the frontend origin(s) in production")
            if "*" in self.cors_origin_list:
                raise RuntimeError("CORS_ORIGINS must not contain a wildcard")


@lru_cache
def get_settings() -> Settings:
    return Settings()
