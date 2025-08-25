# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str = "postgresql://user:password@localhost/hrdb"

    # OpenAI API
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Anthropic API (если будем использовать Claude)
    ANTHROPIC_API_KEY: Optional[str] = None

    # Приложение
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis (опционально)
    REDIS_URL: Optional[str] = "redis://localhost:6379"

    class Config:
        env_file = ".env"


settings = Settings()

# -------------------