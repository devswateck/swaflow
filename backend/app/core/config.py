from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Swatek Flow AI"
    app_env: str = "development"
    database_url: str = "mysql+pymysql://ai_sales:ai_sales_password@localhost:3306/ai_sales?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = Field(default="change_me", min_length=8)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    openai_api_key: str | None = None
    whatsapp_verify_token: str | None = None
    whatsapp_app_secret: str | None = None
    whatsapp_graph_api_version: str = "v25.0"
    public_base_url: str = "http://localhost:8000"
    encryption_key: str | None = None
    n8n_webhook_url: str | None = None
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
