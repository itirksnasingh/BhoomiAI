from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BhoomiAI API"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    allowed_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174"
    )

    allowed_hosts: str = (
        "localhost,"
        "127.0.0.1"
    )

    max_upload_size_mb: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def host_allowlist(self) -> list[str]:
        return [
            host.strip()
            for host in self.allowed_hosts.split(",")
            if host.strip()
        ]

    @model_validator(mode="after")
    def validate_security_settings(self):
        environment = self.environment.lower().strip()

        if self.access_token_expire_minutes <= 0:
            raise ValueError(
                "access_token_expire_minutes must be greater than zero."
            )

        if self.max_upload_size_mb <= 0:
            raise ValueError(
                "max_upload_size_mb must be greater than zero."
            )

        if environment in {"production", "prod"}:
            if len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "Production JWT_SECRET_KEY must be at least 32 characters."
                )

            if self.jwt_algorithm != "HS256":
                raise ValueError(
                    "Only the configured HS256 JWT algorithm is supported."
                )

            if not self.cors_origins:
                raise ValueError(
                    "Production requires at least one allowed CORS origin."
                )

            if not self.host_allowlist:
                raise ValueError(
                    "Production requires at least one allowed host."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
