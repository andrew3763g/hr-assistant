# backend/app/services/api_key_manager.py
"""
Менеджер API ключей - хранит ключи в памяти на время сессии.
Для production можно использовать Redis или зашифрованное хранилище.
"""
from typing import Optional, Dict
import os


class APIKeyManager:
    _instance = None
    _keys: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._keys = {}
        return cls._instance

    def set_openai_key(self, key: str) -> bool:
        """Устанавливает OpenAI API ключ для текущей сессии"""
        if key and key.startswith('sk-'):
            self._keys['openai'] = key
            os.environ['OPENAI_API_KEY'] = key  # Для библиотеки openai
            return True
        return False

    def get_openai_key(self) -> Optional[str]:
        """Получает OpenAI API ключ"""
        # Сначала проверяем сохраненный ключ
        if 'openai' in self._keys:
            return self._keys['openai']
        # Потом переменную окружения (для локальной разработки)
        key = os.getenv('OPENAI_API_KEY')
        if key:
            self._keys['openai'] = key
        return key

    def has_openai_key(self) -> bool:
        """Проверяет наличие OpenAI ключа"""
        return self.get_openai_key() is not None

    def clear_keys(self):
        """Очищает все ключи"""
        self._keys = {}
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']


# Глобальный экземпляр
api_key_manager = APIKeyManager()