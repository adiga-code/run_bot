from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Workout


class WorkoutService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        level: int,
        day: int,
        version: str,
        strength_format: str | None = None,
    ) -> Workout | None:
        """
        Fetch a specific workout.
        For strength days, pass strength_format ('gym'/'home') to get the right template.
        Falls back to 'recovery' version if exact version is missing.
        """
        query = select(Workout).where(
            Workout.level == level,
            Workout.day == day,
            Workout.version == version,
        )
        if strength_format is not None:
            query = query.where(Workout.strength_format == strength_format)
        else:
            query = query.where(Workout.strength_format == None)

        result = await self.session.execute(query)
        workout = result.scalar_one_or_none()

        # Fallback 1: try without strength_format filter (e.g. custom добавка days)
        if workout is None and strength_format is not None:
            result2 = await self.session.execute(
                select(Workout).where(
                    Workout.level == level,
                    Workout.day == day,
                    Workout.version == version,
                    Workout.strength_format == None,
                )
            )
            workout = result2.scalar_one_or_none()

        # Fallback 2: downgrade version to 'recovery'
        if workout is None and version != "recovery":
            return await self.get(level, day, "recovery", strength_format)

        return workout

    async def get_day_type(self, level: int, day: int) -> str | None:
        """Return the day_type for a given level+day."""
        result = await self.session.execute(
            select(Workout.day_type).where(
                Workout.level == level,
                Workout.day == day,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, workout_id: int) -> Workout | None:
        result = await self.session.execute(
            select(Workout).where(Workout.id == workout_id)
        )
        return result.scalar_one_or_none()
