import os
import re
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config object — gives access to values in alembic.ini.
config = context.config

# Set up loggers from the .ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import our models so autogenerate can detect schema changes.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import Base  # noqa: E402
import app.models.models  # noqa: F401, E402 — register all ORM models with Base

target_metadata = Base.metadata


def _sync_url(url: str) -> str:
    """Convert an asyncpg / async URL to a psycopg2-compatible sync URL.

    e.g. postgresql+asyncpg://... → postgresql+psycopg2://...
         postgresql://...         → unchanged (already sync)
    """
    return re.sub(r"postgresql\+asyncpg", "postgresql+psycopg2", url)


def _get_url() -> str:
    """Return the synchronous DB URL for Alembic.

    Priority:
    1. DATABASE_URL env var (converted to sync driver)
    2. sqlalchemy.url from alembic.ini
    """
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return _sync_url(env_url)
    ini_url = config.get_main_option("sqlalchemy.url", "")
    return _sync_url(ini_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the live DB)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        configuration,
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
