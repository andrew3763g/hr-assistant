from __future__ import annotations
import os, sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Импортируем Base и МОДЕЛИ (чтобы их таблицы попали в metadata)
from backend.app.database import Base
import backend.app.models.candidate  # noqa: F401
import backend.app.models.vacancy    # noqa: F401
import backend.app.models.interview  # noqa: F401
import backend.app.models.evaluation # noqa: F401
import backend.app.models.interview_message  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Разрешаем задавать URL через переменную окружения
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Запуск миграций в 'offline'-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в 'online'-режиме."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
