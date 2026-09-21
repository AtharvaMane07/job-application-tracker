from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """
        Hosting providers (Railway, Render, Heroku) commonly hand out
        DATABASE_URL as postgres:// or postgresql:// — psycopg2 needs the
        driver explicit in the scheme. Normalize here so deployment never
        depends on manually rewriting a platform-provided variable.
        """
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+psycopg2://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v


settings = Settings()
