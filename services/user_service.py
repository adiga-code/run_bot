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

    def _max_day(self, user: User) -> int:
        """Returns the maximum program day for this user (28 or 42 if week 5/6 is activated)."""
        return 42 if getattr(user, "extended_week5", False) else 28

    async def current_calendar_day(self, user: User) -> int | None:
        """
        Returns the user's real calendar day in the program (1-28 or 1-35).
        Never decreases — always delta+1 regardless of week repeats.
        Shown in UI as "День X из 28/35".
        """
        if not user.program_start_date:
            return None
        delta = (date.today() - user.program_start_date).days
        return max(1, min(self._max_day(user), delta + 1))

    async def current_template_day(self, user: User) -> int | None:
        """
        Returns the training-template day (1-28 or 1-35) used for workout lookup.
        Subtracts 7 per week_repeat_count so the user re-runs the same
        workout week when they underperformed.

        Hard rule: from calendar day 22 onward, template day always equals
        calendar day — users are forced into week 4 regardless of repeat count.
        Week repeats only apply to weeks 1 and 2 (calendar days 1-21).
        Week 5 (days 29-35) is only available when extended_week5=True.
        """
        if not user.program_start_date:
            return None
        delta = (date.today() - user.program_start_date).days
        calendar_day = delta + 1
        day_index = calendar_day - (user.week_repeat_count * 7)
        # From day 22 onward: always week 4+, no rollback
        if calendar_day >= 22:
            day_index = calendar_day
        return max(1, min(self._max_day(user), day_index))

    # Keep legacy name as alias for template day — used in log creation and
    # workout lookups. Do NOT use for display; use current_calendar_day instead.
    async def current_program_day(self, user: User) -> int | None:
        return await self.current_template_day(user)

    def log_calendar_day(self, user: User, log) -> int:
        """
        Compute the calendar day for a historical log entry.
        Uses the log's actual date so it is always correct regardless of
        when week_repeat_count was changed.
        """
        if not user.program_start_date:
            return log.day_index
        delta = (log.date - user.program_start_date).days
        return max(1, min(28, delta + 1))

    def current_week_range(self, day_index: int) -> tuple[int, int]:
        """Returns (week_start_day, week_end_day) for the given day_index."""
        week_num = (day_index - 1) // 7          # 0-based week number
        start = week_num * 7 + 1
        end = min(start + 6, 28)
        return start, end

    async def reset_progress(self, user: User) -> User:
        """Reset user to pre-onboarding state so they can start over."""
        from sqlalchemy import delete
        from database.models import SessionLog
        # Delete ALL session logs for this user, not just today's
        await self.session.execute(
            delete(SessionLog).where(SessionLog.user_id == user.telegram_id)
        )
        await self.session.commit()
        return await self.update(
            user,
            onboarding_complete=False,
            status="pending",
            program_start_date=None,
            level=None,
            week_repeat_count=0,
        )

    async def all_active(self) -> list[User]:
        """Returns users whose program is running (status=active)."""
        result = await self.session.execute(
            select(User).where(
                User.is_active == True,
                User.onboarding_complete == True,
                User.status == "active",
            )
        )
        return list(result.scalars().all())
