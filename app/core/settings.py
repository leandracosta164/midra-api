from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Application and database configuration loaded from .env."""

    APP_NAME: str = "MIDRA API"
    APP_VERSION: str = "0.4.2"
    APP_ENV: str = "development"
    DEBUG: bool = True

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "midra"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str

    MIDRA_ENGINEERING_ADMIN_EMAIL: str | None = None
    MIDRA_ENGINEERING_ADMIN_PASSWORD: str | None = None
    MIDRA_ENGINEERING_SESSION_HOURS: int = 12
    MIDRA_ENGINEERING_WEB_ORIGIN: str | None = None
    MIDRA_API_PUBLIC_ORIGIN: str | None = None
    MIDRA_API_ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver"
    MIDRA_WORKPLACE_WEB_ORIGIN: str | None = None
    MIDRA_PROPERTY_WEB_ORIGINS: str = (
        "http://localhost:4322,http://127.0.0.1:4322,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    MIDRA_PROPERTY_ADMIN_EMAIL: str | None = None
    MIDRA_PROPERTY_ADMIN_PASSWORD: str | None = None
    MIDRA_PROPERTY_AUTH_SECRET: str | None = None
    MIDRA_PROPERTY_SESSION_HOURS: int = 12
    MIDRA_ENGINEERING_FILE_ROOT: str = ".midra_engineering_files"
    MIDRA_ENGINEERING_MAX_FILE_MB: int = 25
    MIDRA_LOG_LEVEL: str = "INFO"
    MIDRA_REQUEST_ID_HEADER: str = "X-Request-ID"
    MIDRA_ENGINEERING_MAX_REQUEST_MB: int = 40
    MIDRA_PROPOSAL_EMAIL_HOST: str | None = None
    MIDRA_PROPOSAL_EMAIL_PORT: int = 587
    MIDRA_PROPOSAL_EMAIL_USERNAME: str | None = None
    MIDRA_PROPOSAL_EMAIL_PASSWORD: str | None = None
    MIDRA_PROPOSAL_EMAIL_FROM: str | None = None
    MIDRA_PROPOSAL_EMAIL_USE_TLS: bool = True
    MIDRA_PROPOSAL_EMAIL_USE_SSL: bool = False
    MIDRA_PROPOSAL_RESPONSE_SECRET: str | None = None
    MIDRA_PROPOSAL_RESPONSE_TTL_DAYS: int = 30
    MIDRA_PROPERTY_PUBLIC_ORIGIN: str | None = None
    ECODE360_API_KEY: str | None = None
    ECODE360_API_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def PROPERTY_WEB_ORIGINS(self) -> list[str]:
        """Return normalized Property web origins from deployment configuration."""
        values = [
            item.strip().rstrip("/")
            for item in self.MIDRA_PROPERTY_WEB_ORIGINS.split(",")
            if item.strip()
        ]
        return list(dict.fromkeys(values))

    @property
    def API_ALLOWED_HOSTS(self) -> list[str]:
        """Return normalized API Host-header allowlist entries."""
        values = [
            item.strip().lower().rstrip(".")
            for item in self.MIDRA_API_ALLOWED_HOSTS.split(",")
            if item.strip()
        ]
        return list(dict.fromkeys(values))

    @property
    def DATABASE_URL(self) -> URL:
        """Build a safe SQLAlchemy URL, including passwords with special characters."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

