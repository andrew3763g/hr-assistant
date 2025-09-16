# backend/app/database.py
from contextlib import contextmanager
import logging
import time
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool

from .config import settings

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- URL БД (безопасный фоллбек) ---
DB_URL = getattr(settings, "db_url", None) or getattr(settings, "DATABASE_URL", None)
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not configured")

engine = create_engine(
    DB_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
    connect_args={"connect_timeout": 10, "options": "-c timezone=utc"},
)
if getattr(settings, "DEBUG", False):
    engine.echo = True

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()
Base.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

@event.listens_for(Pool, "connect")
def on_connect(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("SET statement_timeout = '30s'")
    cur.close()

@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_conn, *_):
    cur = dbapi_conn.cursor()
    try:
        cur.execute("SELECT 1")
    finally:
        cur.close()

# --- ЕДИНСТВЕННЫЙ dependency с автокоммитом ---
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_database():
    """Создание таблиц + индексы (вызов по необходимости)."""
    try:
        # ВАЖНО: корректный импорт моделей, чтобы они зарегистрировались в Base.metadata
        from backend.app.models import candidate, vacancy, interview, evaluation  # noqa: F401

        logger.info("Создание таблиц...")
        Base.metadata.create_all(bind=engine)

        with engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_evaluations_score ON evaluations(total_score DESC);
            """))
            conn.commit()

        logger.info("✓ База инициализирована")
        check_database_connection()
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise

def check_database_connection() -> bool:
    for attempt in range(3):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).fetchone()
                logger.info("✓ Подключение к БД OK")
                return True
        except Exception as e:
            logger.warning(f"Попытка {attempt+1}/3 подключения к БД не удалась: {e}")
            time.sleep(2)
    logger.error("✗ Не удалось подключиться к БД")
    return False

def get_database_stats() -> dict:
    stats = {}
    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        ))]
        for t in tables:
            try:
                stats[t] = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
            except Exception as e:
                stats[t] = f"Error: {e}"
    return stats

__all__ = ["engine", "SessionLocal", "Base", "get_db", "get_db_session",
           "init_database", "check_database_connection", "get_database_stats"]
