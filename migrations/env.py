# migrations/env.py
from __future__ import annotations
from backend.app.config import settings
from backend.app.database import Base

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

load_dotenv()

# --- bootstrap project and .env ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../hr-assistant
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.docker", override=True)

# Import app bits AFTER sys.path/.env
import backend.app.models  # noqa: F401  # registers all models

config = context.config

# ---------- SINGLE source of DSN (string) ----------
# Precedence:
#   1) ALEMBIC_DATABASE_URL (explicit override for migrations)
#   2) DATABASE_URL (shared default)
#   3) settings.db_url (same resolver as the application runtime)
dsn = (
    os.getenv("ALEMBIC_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or getattr(settings, "db_url", None)
    or getattr(settings, "DATABASE_URL", None)
)
if dsn is None:
    raise RuntimeError("Database URL is not configured")

config.set_main_option("sqlalchemy.url", str(dsn))
# -----------------------------------

# Logging config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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
