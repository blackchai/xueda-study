from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STUDYMATE_",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+aiosqlite:///./studymate_dev.db"
    migration_database_url: str = ""
    public_origin: str = ""
    auto_create_schema: bool = False
    frontend_dist_dir: str = ""
    canonical_host: str = ""

    auth_signing_secret: str = "development-only-change-before-deploying"
    auth_cookie_name: str = "studymate_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_session_days: int = 30
    login_max_failures: int = 5
    login_window_minutes: int = 15
    login_lock_minutes: int = 15
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    buddy_invites_per_hour: int = Field(default=10, ge=1, le=500)
    buddy_invites_per_day: int = Field(default=30, ge=1, le=1000)
    buddy_pending_limit: int = Field(default=20, ge=1, le=200)
    buddy_pair_cooldown_seconds: int = Field(default=300, ge=0, le=86400)

    @field_validator("database_url", "migration_database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_for_startup(self) -> None:
        if not 1 <= self.auth_session_days <= 90:
            raise ValueError("STUDYMATE_AUTH_SESSION_DAYS must be between 1 and 90")
        if not 3 <= self.login_max_failures <= 20:
            raise ValueError("STUDYMATE_LOGIN_MAX_FAILURES must be between 3 and 20")
        if not 1 <= self.login_window_minutes <= 120:
            raise ValueError("STUDYMATE_LOGIN_WINDOW_MINUTES must be between 1 and 120")
        if not 1 <= self.login_lock_minutes <= 1440:
            raise ValueError("STUDYMATE_LOGIN_LOCK_MINUTES must be between 1 and 1440")
        if self.app_env == "production":
            if self.auth_signing_secret in {"development-only-change-before-deploying", "replace-with-a-long-random-secret", "replace-with-at-least-32-random-bytes"}:
                raise ValueError("production requires a unique authentication signing secret")
            if len(self.auth_signing_secret.encode("utf-8")) < 32:
                raise ValueError("production auth signing secret must be at least 32 bytes")
            if not self.auth_cookie_secure:
                raise ValueError("production authentication cookies must be Secure")
            if not self.database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("production requires PostgreSQL")
            if self.auto_create_schema:
                raise ValueError("production schema changes must use Alembic")


@lru_cache
def get_settings() -> Settings:
    return Settings()
