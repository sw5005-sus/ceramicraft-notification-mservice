from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    POSTGRES_USER: str = Field(default="user")
    POSTGRES_PASSWORD: str = Field(default="password")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    NOTIFICATION_DB_NAME: str = "notification_db"

    NOTIFICATION_HTTP_HOST: str = "0.0.0.0"
    NOTIFICATION_HTTP_PORT: int = 8080
    NOTIFICATION_GRPC_HOST: str = "[::]"
    NOTIFICATION_GRPC_PORT: int = 50051

    FIREBASE_CREDENTIALS_JSON: str = Field(default="")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.NOTIFICATION_DB_NAME}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
