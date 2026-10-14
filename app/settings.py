from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.secrets_store import persist_or_read_session_key

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_DEFAULT_DB_PASSWORD = "ateam-local-dev"
PLACEHOLDER_VALUES = frozenset(
    {
        "change-me",
        "changeme",
        "CHANGE-ME",
        DEV_DEFAULT_DB_PASSWORD,
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    database_url: str = ""
    ateam_secret_key: str = ""
    host_bind: str = "127.0.0.1"
    version: str = "0.1.0"
    image_tag: str = "0.1.0-dev"
    postgres_user: str = "ateam"
    postgres_db: str = "ateam"
    postgres_password: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    anthropic_api_key: str = ""
    postmark_api_token: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    config_dir: str = str(REPO_ROOT / "config")
    skills_dir: str = str(REPO_ROOT / "skills")
    prompts_dir: str = str(REPO_ROOT / "prompts")
    data_dir: str = str(REPO_ROOT / "data")
    session_hours: int = 8

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        password = self.postgres_password or DEV_DEFAULT_DB_PASSWORD
        return (
            f"postgresql+psycopg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def resolved_secret_key(self) -> str:
        if self.ateam_secret_key:
            return self.ateam_secret_key
        if self.is_production:
            return ""
        return persist_or_read_session_key(self.data_dir)


def load_settings() -> Settings:
    return Settings()
