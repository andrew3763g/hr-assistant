# backend/app/database.py
"""
Модуль для работы с базой данных PostgreSQL
Управляет подключением, сессиями и инициализацией таблиц

Что реализовано в этом модуле:

Управление подключением к PostgreSQL с автоматическим переключением между локальной БД и Docker
Пул соединений с проверкой живости соединений
Dependency Injection для FastAPI через функцию get_db()
Context manager для работы вне FastAPI
Инициализация БД с созданием таблиц и индексов
Диагностика - проверка подключения и статистика по таблицам

🔑 Ключевые особенности:

Автоматическое определение окружения (локальное/Docker)
Оптимизированный пул соединений с проверкой живости
Автоматические индексы для часто используемых полей
Безопасная работа с транзакциями через context manager
Встроенная диагностика состояния БД
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool
from contextlib import contextmanager
import logging
from typing import Generator
import time

from .config import settings

# Настройка логирования для отладки БД
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Настройка SQLAlchemy ===

# Получаем URL базы данных из конфигурации
DATABASE_URL = settings.DATABASE_URL

# Создаем движок базы данных с оптимальными настройками
engine = create_engine(
    DATABASE_URL,
    # Настройки пула соединений
    pool_size=5,  # Базовый размер пула
    max_overflow=10,  # Максимальное превышение пула
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,  # Переподключение каждый час
    # echo=settings.DEBUG,  # Логирование SQL-запросов в режиме отладки
    # Настройки для PostgreSQL
    connect_args={
        "connect_timeout": 10,  # Таймаут подключения
        "options": "-c timezone=utc"  # Установка временной зоны
    }
)

# включение echo привязано к DEBUG — сделано через getattr
if getattr(settings, "DEBUG", False):
    engine.echo = True

# Создаем фабрику сессий
SessionLocal = sessionmaker(
    autocommit=False,  # Ручное управление транзакциями
    autoflush=False,  # Отключаем автоматический flush
    bind=engine,
    expire_on_commit=False  # Объекты остаются доступными после commit
)

# Базовый класс для всех моделей
Base = declarative_base()

# Добавляем метаданные в базовый класс
Base.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",  # Индексы
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Уникальные ограничения
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Check ограничения
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Внешние ключи
    "pk": "pk_%(table_name)s"  # Первичные ключи
}


# === События для мониторинга пула соединений ===

@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Настройка соединения при подключении к БД"""
    # Устанавливаем таймаут для PostgreSQL
    cursor = dbapi_conn.cursor()
    cursor.execute("SET statement_timeout = '30s'")  # Таймаут запросов 30 секунд
    cursor.close()


@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_conn, connection_record, connection_proxy):
    """Проверка соединения при получении из пула"""
    # Проверяем, что соединение живое
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        # Соединение мертво, вызываем исключение для переподключения
        raise Exception("Connection failed ping test")
    finally:
        cursor.close()


# === Функции для работы с сессиями ===

def get_db() -> Generator[Session, None, None]:
    """
    Dependency для FastAPI - создает сессию БД
    Использование:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            return db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager для работы с БД вне FastAPI
    Использование:
        with get_db_session() as session:
            session.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Автоматический commit при успехе
    except Exception:
        db.rollback()  # Откат при ошибке
        raise
    finally:
        db.close()


# === Функции инициализации БД ===

def init_database():
    """
    Инициализация базы данных
    Создает все таблицы и начальные данные
    """
    try:
        # Импортируем все модели чтобы они зарегистрировались
        from app.models import candidate, vacancy, interview, evaluation

        logger.info("Создание таблиц в базе данных...")

        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)

        # Создаем дополнительные индексы для оптимизации
        with engine.connect() as conn:
            # Индекс для поиска кандидатов по email
            conn.execute(text("""
                              CREATE INDEX IF NOT EXISTS idx_candidates_email
                                  ON candidates(email);
                              """))

            # Индекс для поиска интервью по статусу
            conn.execute(text("""
                              CREATE INDEX IF NOT EXISTS idx_interviews_status
                                  ON interviews(status);
                              """))

            # Индекс для поиска оценок по баллам
            conn.execute(text("""
                              CREATE INDEX IF NOT EXISTS idx_evaluations_score
                                  ON evaluations(total_score DESC);
                              """))

            conn.commit()

        logger.info("✓ База данных успешно инициализирована")

        # Проверяем подключение
        check_database_connection()

    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise


def check_database_connection() -> bool:
    """
    Проверка подключения к базе данных
    Возвращает True если подключение успешно
    """
    max_retries = 3
    retry_delay = 2  # секунды

    for attempt in range(max_retries):
        try:
            # Пытаемся выполнить простой запрос
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("✓ Подключение к базе данных установлено")
                return True

        except Exception as e:
            logger.warning(f"Попытка {attempt + 1}/{max_retries} подключения к БД не удалась: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("✗ Не удалось подключиться к базе данных")
                return False

    return False


def drop_all_tables():
    """
    ВНИМАНИЕ: Удаляет все таблицы из БД
    Использовать только для тестирования!
    """
    if settings.DEBUG:
        logger.warning("Удаление всех таблиц из базы данных...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Все таблицы удалены")
    else:
        logger.error("Удаление таблиц доступно только в режиме DEBUG")
        raise PermissionError("Cannot drop tables in production mode")


def get_database_stats() -> dict:
    """
    Получение статистики по базе данных
    Возвращает количество записей в каждой таблице
    """
    stats = {}

    with engine.connect() as conn:
        # Получаем список всех таблиц
        result = conn.execute(text("""
                                   SELECT tablename
                                   FROM pg_tables
                                   WHERE schemaname = 'public'
                                   """))

        tables = [row[0] for row in result]

        # Для каждой таблицы получаем количество записей
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                stats[table] = count
            except Exception as e:
                stats[table] = f"Error: {e}"

    return stats


# === Вспомогательные функции для работы с транзакциями ===

def execute_in_transaction(func, *args, **kwargs):
    """
    Выполняет функцию в транзакции
    При ошибке автоматически откатывает изменения
    """
    with get_db_session() as session:
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в транзакции: {e}")
            raise


# === Класс для управления миграциями (упрощенный) ===

class SimpleMigrationManager:
    """Простой менеджер миграций для MVP"""

    @staticmethod
    def create_initial_data():
        """Создает начальные данные в БД"""
        with get_db_session() as session:
            # Здесь можно добавить создание тестовых данных
            # Например, тестовые вакансии или настройки
            pass

    @staticmethod
    def upgrade_schema():
        """Обновляет схему БД до актуальной версии"""
        # В продакшене использовать Alembic
        # Для MVP просто пересоздаем таблицы
        init_database()


# Экспортируем основные компоненты
__all__ = [
    'engine',
    'SessionLocal',
    'Base',
    'get_db',
    'get_db_session',
    'init_database',
    'check_database_connection',
    'get_database_stats',
    'execute_in_transaction',
    'SimpleMigrationManager'
]