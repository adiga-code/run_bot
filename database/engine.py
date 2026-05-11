import json
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from config import settings
from database.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False)
session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_db() -> None:
    """Create initial tables (new installs only) and run Alembic migrations."""
    # create_all создаёт таблицы только если их нет (безопасно для существующих БД)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_alembic_migrations()


async def _run_alembic_migrations() -> None:
    """
    Запускаем pending Alembic-миграции при старте.
    Безопасно при многократных запусках — применяются только новые версии.
    """
    try:
        import asyncio
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        # Suppress noisy alembic startup lines
        logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
        # Запускаем в отдельном потоке, т.к. Alembic sync API
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: command.upgrade(alembic_cfg, "head"))
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        # Не падаем если Alembic не настроен или уже на head
        logger.warning("Alembic migration skipped: %s", e)


async def seed_workouts() -> None:
    """Load workouts from data/workouts.json into DB (upsert on every restart)."""
    data_path = Path(__file__).parent.parent / "data" / "workouts.json"
    if not data_path.exists():
        return

    from database.models import Workout
    from sqlalchemy import select

    with open(data_path, encoding="utf-8") as f:
        workouts_data = json.load(f)

    async with session_maker() as session:
        for item in workouts_data:
            result = await session.execute(
                select(Workout).where(
                    Workout.level == item["level"],
                    Workout.day == item["day"],
                    Workout.version == item["version"],
                    Workout.strength_format == item.get("strength_format"),
                )
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                session.add(Workout(**item))
            else:
                existing.title = item["title"]
                existing.text = item["text"]
                existing.day_type = item.get("day_type", existing.day_type)
        await session.commit()
