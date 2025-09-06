# backend/app/config.py
"""
Модуль конфигурации приложения HR AI Assistant
Что реализовано в этом модуле:

Управление всеми настройками - от БД до AI провайдеров
Подготовка к миграции - параметр AI_PROVIDER для переключения между OpenAI и локальными моделями
Загрузка конфигураций - автоматическая загрузка вопросов и критериев из JSON
Проверка готовности - функция check_system_ready() для диагностики
Управление API ключами - ввод ключей при старте системы
Работа с Google Drive - хранение ID папок и путь к service account

🔑 Ключевые моменты:

API ключи не хранятся в коде, вводятся при старте
Легкое переключение между AI провайдерами через AI_PROVIDER
Все пути и ID папок Google Drive вынесены в конфигурацию
Критерии оценки загружаются из внешнего файла (легко редактировать)

Управляет всеми настройками системы, API ключами и путями к файлам
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any
import os
from pathlib import Path
import json


class Settings(BaseSettings):
    """Основные настройки приложения"""

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',  # игнорировать переменные, которых нет в модели
    )

    # === Базовые настройки приложения ===
    APP_NAME: str = "HR AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # === База данных ===
    DATABASE_URL: str = "postgresql://hruser:hrpassword@localhost:5432/hrdb"
    # Для Docker контейнера
    DATABASE_URL_DOCKER: str = "postgresql://hruser:hrpassword@postgres:5432/hrdb"

    # === API ключи (вводятся при старте) ===
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"  # Модель для парсинга и анализа
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # Модель для эмбеддингов
    OPENAI_TTS_MODEL: str = "tts-1"  # Модель для озвучки
    OPENAI_TTS_VOICE: str = "onyx"  # Голос Густаво (низкий баритон)
    OPENAI_STT_MODEL: str = "whisper-1"  # Модель для расшифровки речи

    # === Google Drive ===
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "service_account.json"
    GOOGLE_DRIVE_FOLDERS: Optional[Dict[str, str]] = None  # Загружается из JSON

    # === Выбор AI провайдера (для будущей миграции) ===
    AI_PROVIDER: str = "openai"  # Может быть: "openai", "local", "gemini"
    LOCAL_MODEL_PATH: Optional[str] = None  # Путь к локальной модели (на будущее)

    # === Настройки интервью ===
    INTERVIEW_MAX_DURATION_MINUTES: int = 60  # Максимальная длительность интервью
    ANSWER_TIME_LIMIT_SECONDS: int = 180  # 3 минуты на ответ
    QUESTIONS_FILE: str = "questions.json"  # Файл с базовыми вопросами
    EVALUATION_CRITERIA_FILE: str = "evaluation_criteria.json"  # Критерии оценки

    # === Настройки оценки ===
    MIN_RESPONSE_RATE: float = 0.7  # Минимальный процент ответов (70%)
    CONFIDENCE_THRESHOLD: float = 0.9  # Порог уверенности для бонуса
    CONFIDENCE_BONUS: float = 0.3  # Бонус за уверенные ответы (30%)
    TOP_CANDIDATES_COUNT: int = 5  # Количество кандидатов на следующий этап
    RESERVE_CANDIDATES_COUNT: int = 5  # Количество кандидатов в резерв

    # === Пути к файлам данных ===
    DATA_DIR: Path = Path(__file__).parent / "data"
    UPLOADS_DIR: Path = Path(__file__).parent / "uploads"
    TEMP_DIR: Path = Path(__file__).parent / "temp"

    # === Настройки сервера ===
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    # === Безопасность ===
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # class Config:
    #     """Настройки Pydantic"""
    #     env_file = ".env"
    #     case_sensitive = True

    def __init__(self, **kwargs):
        """Инициализация с загрузкой дополнительных файлов"""
        super().__init__(**kwargs)
        self._load_gdrive_folders()
        self._create_directories()

    def _load_gdrive_folders(self):
        """Загружает ID папок Google Drive из JSON файла"""
        try:
            gdrive_config_path = self.DATA_DIR / "gdrive_folders.json"
            if gdrive_config_path.exists():
                with open(gdrive_config_path, 'r', encoding='utf-8') as f:
                    self.GOOGLE_DRIVE_FOLDERS = json.load(f)
            else:
                # Значения по умолчанию (нужно будет заменить на реальные)
                self.GOOGLE_DRIVE_FOLDERS = {
                    "resumes": "1U9pZtW1dZ9dZxjZ3_L8IeONTOsn6Jj8N",
                    "vacancies": "1dhL1s3TRmlcAImPwxl9bdbnIQWRzEkBg",
                    "audio": "12rlp3qCB-17m7RAYHNmsA14RO3Zpxu3V",
                    "text": "1UR35VxnnQadUZxt5WgjcqIJ3olr6O0Ka",
                    "reports": "1HoWTQTHo4jz9ynCLcpC0PnwI01fAYIdW",
                    "questions": "1m7yu8EbRm8S6ehlvcd1xsucELIcJCTMRDS_U8b3bEeM"
                }
        except Exception as e:
            print(f"Ошибка загрузки конфигурации Google Drive: {e}")
            self.GOOGLE_DRIVE_FOLDERS = {}

    def _create_directories(self):
        """Создает необходимые директории если их нет"""
        for directory in [self.DATA_DIR, self.UPLOADS_DIR, self.TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    def load_questions(self) -> list:
        """Загружает вопросы интервью из JSON файла"""
        questions_path = self.DATA_DIR / self.QUESTIONS_FILE
        try:
            if questions_path.exists():
                with open(questions_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"Файл вопросов не найден: {questions_path}")
                return []
        except Exception as e:
            print(f"Ошибка загрузки вопросов: {e}")
            return []

    def load_evaluation_criteria(self) -> dict:
        """Загружает критерии оценки из JSON файла"""
        criteria_path = self.DATA_DIR / self.EVALUATION_CRITERIA_FILE
        try:
            if criteria_path.exists():
                with open(criteria_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Возвращаем критерии по умолчанию
                return {
                    "auto_reject": {
                        "identity_mismatch": ["name", "gender", "age"],
                        "red_flags": list(range(7, 21)),  # Вопросы 7-20
                        "min_response_rate": self.MIN_RESPONSE_RATE
                    },
                    "scoring": {
                        "base_score_per_answer": 1,
                        "no_answer_penalty": 0,
                        "skill_no_answer_penalty": -0.5,
                        "confidence_bonus": self.CONFIDENCE_BONUS,
                        "confidence_threshold": self.CONFIDENCE_THRESHOLD
                    },
                    "ranking": {
                        "next_stage": self.TOP_CANDIDATES_COUNT,
                        "reserve": self.RESERVE_CANDIDATES_COUNT
                    }
                }
        except Exception as e:
            print(f"Ошибка загрузки критериев оценки: {e}")
            return {}

    def get_database_url(self) -> str:
        """Возвращает URL базы данных в зависимости от окружения"""
        # Проверяем, работаем ли мы в Docker
        if os.path.exists('/.dockerenv'):
            return self.DATABASE_URL_DOCKER
        return self.DATABASE_URL

    def is_ai_configured(self) -> bool:
        """Проверяет, настроен ли AI провайдер"""
        if self.AI_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.startswith('sk-'))
        elif self.AI_PROVIDER == "local":
            return bool(self.LOCAL_MODEL_PATH and Path(self.LOCAL_MODEL_PATH).exists())
        return False

    def set_api_key(self, key: str, provider: str = "openai"):
        """Устанавливает API ключ для провайдера"""
        if provider == "openai":
            self.OPENAI_API_KEY = key
            os.environ['OPENAI_API_KEY'] = key
            print(f"✓ OpenAI API ключ установлен")

    def get_gdrive_folder_id(self, folder_type: str) -> Optional[str]:
        """Получает ID папки Google Drive по типу"""
        if self.GOOGLE_DRIVE_FOLDERS:
            return self.GOOGLE_DRIVE_FOLDERS.get(folder_type)
        return None


# Создаем глобальный экземпляр настроек
settings = Settings()


# Функция для проверки готовности системы
def check_system_ready() -> tuple[bool, list[str]]:
    """
    Проверяет готовность всех компонентов системы
    Возвращает (готовность, список проблем)
    """
    issues = []

    # Проверка AI
    if not settings.is_ai_configured():
        issues.append("AI провайдер не настроен. Введите API ключ.")

    # Проверка Google Service Account
    service_account_path = Path(settings.GOOGLE_SERVICE_ACCOUNT_FILE)
    if not service_account_path.exists():
        issues.append(f"Файл service account не найден: {service_account_path}")

    # Проверка папок данных
    if not settings.DATA_DIR.exists():
        issues.append(f"Директория данных не найдена: {settings.DATA_DIR}")

    # Проверка файла вопросов
    questions_path = settings.DATA_DIR / settings.QUESTIONS_FILE
    if not questions_path.exists():
        issues.append(f"Файл вопросов не найден: {questions_path}")

    return len(issues) == 0, issues


# Экспортируем для удобного импорта
__all__ = ['settings', 'Settings', 'check_system_ready']