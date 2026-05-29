"""
configmanagemodule
use pydantic-settings fromring境changeamount  .env fileloadconfig
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应useconfig"""

    # DeepSeek API
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"

    # LLM provider selection
    LLM_PROVIDER: str = "deepseek"

    # datalib
    DATABASE_URL: str = "sqlite:///./cyber_trainer.db"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24smallwhen

    # towardamountdatalib
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION: str = "fitness_knowledge"

    # Embeddingmodel
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"

    # servicetasker
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """getgetconfigsingle例"""
    return Settings()
