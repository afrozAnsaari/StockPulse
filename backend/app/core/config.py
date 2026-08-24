import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockPulse"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./stockpulse.db")
    
    # LLM Configuration
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://litellm-qc.zycus.net/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-cursor")
    LLM_PRODUCT: str = os.getenv("LLM_PRODUCT", "PC1")
    
    # Strategy & Thresholds
    ACTIVE_STRATEGY: str = os.getenv("ACTIVE_STRATEGY", "ai")  # "ai" or "rule"
    DEMAND_SPIKE_MULTIPLIER: float = 3.0
    PRICE_MAX_MULTIPLIER: float = 3.0
    PRICE_MIN_MULTIPLIER: float = 0.3
    
    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:8000")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()