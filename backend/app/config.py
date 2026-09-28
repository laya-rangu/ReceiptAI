from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./data/receiptai.db"
    storage_path: Path = Path("./data/files")
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    seed_demo: bool = True
    job_mode: str = "inline"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    extraction_model: str = "gpt-4.1-mini"


settings = Settings()
