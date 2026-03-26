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
        ("users",        "status",       "VARCHAR(20) DEFAULT 'active'"),
        ("users",        "q_runs",       "VARCHAR(10)"),
        ("users",        "q_structure",  "VARCHAR(10)"),
        ("session_logs", "stress_level", "INTEGER"),
        ("session_logs", "red_flag",     "BOOLEAN DEFAULT FALSE"),
        ("session_logs", "fatigue_reduction", "BOOLEAN DEFAULT FALSE"),
        ("session_logs", "morning_sent", "BOOLEAN DEFAULT FALSE"),
        ("session_logs", "evening_sent", "BOOLEAN DEFAULT FALSE"),
    ]
    async with engine.begin() as conn:
        for table, column, definition in migrations:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            )


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
