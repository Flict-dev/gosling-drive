from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gosling Drive"
    app_env: str = "local"
    debug: bool = True

    database_url: str = "postgresql+psycopg://gosling:gosling@localhost:5432/gosling_drive"

    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "gosling-drive"
    s3_region: str = "us-east-1"
    s3_presigned_expire_seconds: int = 3600

    upload_part_size: int = 16 * 1024 * 1024
    max_upload_size: int = 10 * 1024 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

