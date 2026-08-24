import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockPulse"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_URL: str = "https://litellm-qc.zycus.net/v1/chat/completions"
    LLM_MODEL: str = "qwen-cursor"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()