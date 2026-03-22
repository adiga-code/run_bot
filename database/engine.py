import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from config import settings
from database.models import Base

engine = create_async_engine(settings.database_url, echo=False)
session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_db() -> None:
    """Create all tables and run incremental migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_db()


async def _migrate_db() -> None:
    """ADD COLUMN IF NOT EXISTS migrations — safe to run on every restart."""
    migrations: list[tuple[str, str, str]] = [
        # (table, column, definition)
        ("users", "status",      "VARCHAR(20) DEFAULT 'active'"),
        ("users", "q_runs",      "VARCHAR(10)"),
        ("users", "q_structure", "VARCHAR(10)"),
    ]
    async with engine.begin() as conn:
        for table, column, definition in migrations:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            )


async def seed_workouts() -> None:
    """Load workouts from data/workouts.json into DB (skip if already loaded)."""
    data_path = Path(__file__).parent.parent / "data" / "workouts.json"
    if not data_path.exists():
        return

    from database.models import Workout
    from sqlalchemy import select

    async with session_maker() as session:
        result = await session.execute(select(Workout).limit(1))
        if result.scalar_one_or_none() is not None:
            return  # already seeded

        with open(data_path, encoding="utf-8") as f:
            workouts_data = json.load(f)

        for item in workouts_data:
            session.add(Workout(**item))
        await session.commit()
