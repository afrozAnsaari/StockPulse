import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockPulse"
    DATABASE_URL: str = "sqlite:///./stockpulse.db"
    
    # LLM Configuration (LiteLLM private OpenAI-compatible gateway)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://litellm-qc.zycus.net/v1"
    LLM_MODEL: str = "qwen-cursor"
    LLM_PRODUCT: str = "PC1"
    LLM_TIMEOUT_SECONDS: float = 15.0
    
    # Strategy & Thresholds
    ACTIVE_STRATEGY: str = "ai"  # "ai" or "rule"
    DEMAND_SPIKE_MULTIPLIER: float = 3.0
    PRICE_MAX_MULTIPLIER: float = 3.0
    PRICE_MIN_MULTIPLIER: float = 0.3
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:8000"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["http://localhost:5173"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()