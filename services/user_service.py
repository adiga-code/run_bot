from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_raise(self, telegram_id: int) -> User:
        user = await self.get(telegram_id)
        if user is None:
            raise ValueError(f"User {telegram_id} not found")
        return user

    async def create(
        self,
        telegram_id: int,
        full_name: str,
        **kwargs,
    ) -> User:
        user = User(telegram_id=telegram_id, full_name=full_name, **kwargs)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_or_create(self, telegram_id: int, full_name: str) -> tuple[User, bool]:
        """Returns (user, created). created=True if new user was inserted."""
        user = await self.get(telegram_id)
        if user:
            return user, False
        user = await self.create(telegram_id=telegram_id, full_name=full_name)
        return user, True

    async def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def current_program_day(self, user: User) -> int | None:
        """
        Returns today's day index (1-28) or None if program not started.
        week_repeat_count shifts the effective day back by 7 per repeat.
        """
        if not user.program_start_date:
            return None
        delta = (date.today() - user.program_start_date).days
        day_index = delta + 1 - (user.week_repeat_count * 7)
        return max(1, min(28, day_index))

    def current_week_range(self, day_index: int) -> tuple[int, int]:
        """Returns (week_start_day, week_end_day) for the given day_index."""
        week_num = (day_index - 1) // 7          # 0-based week number
        start = week_num * 7 + 1
        end = min(start + 6, 28)
        return start, end

    async def all_active(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.is_active == True, User.onboarding_complete == True)
        )
        return list(result.scalars().all())
