import asyncio
import logging

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Don't let alembic reconfigure logging — the app sets up its own logging config
logging.getLogger("alembic").setLevel(logging.WARNING)

# ── Import models so autogenerate sees them ───────────────────────────────────
from database.models import Base  # noqa: E402  (after sys.path setup)
target_metadata = Base.metadata

# ── Override sqlalchemy.url from pydantic settings ───────────────────────────
try:
    from config import settings as app_settings
    # Alembic needs a sync URL for some operations; asyncpg → psycopg2 swap for
    # offline mode. Online mode uses async_engine_from_config directly.
    _db_url = app_settings.database_url
    # Replace async driver prefix so Alembic offline mode works
    _sync_url = (
        _db_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("sqlite+aiosqlite://", "sqlite://")
    )
    config.set_main_option("sqlalchemy.url", _sync_url)
except Exception:
    pass  # URL can be set via alembic.ini or CLI


# ── Offline mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations without a DB connection; emits SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async) ───────────────────────────────────────────────────────
def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from config import settings as app_settings
    connectable = async_engine_from_config(
        {"sqlalchemy.url": app_settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
