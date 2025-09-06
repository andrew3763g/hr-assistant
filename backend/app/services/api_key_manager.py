# backend/app/services/api_key_manager.py
from __future__ import annotations
import os
from typing import Optional, Dict

try:
    # settings подхватывает .env через pydantic-settings
    from backend.app.config import settings  # type: ignore
except Exception:
    settings = None  # на случай запуска из alembic и т.п.

class APIKeyManager:
    """
    Мини-менеджер API-ключей.
    Приоритет: переменные окружения -> settings из .env.
    Поддерживаем "openai" и "anthropic" (второй можно оставить пустым).
    """
    _name_map: Dict[str, tuple[str, ...]] = {
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
    }

    def __init__(self) -> None:
        self._cache: Dict[str, Optional[str]] = {}

    def get(self, provider: str) -> Optional[str]:
        provider = provider.lower()
        if provider in self._cache:
            return self._cache[provider]

        env_names = self._name_map.get(provider, (provider.upper() + "_API_KEY",))
        value: Optional[str] = None

        # 1) env
        for name in env_names:
            value = os.getenv(name)
            if value:
                break

        # 2) settings.*
        if not value and settings is not None:
            for name in env_names:
                value = getattr(settings, name, None)
                if value:
                    break

        self._cache[provider] = value
        return value

    def has(self, provider: str) -> bool:
        return bool(self.get(provider))
