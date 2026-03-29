from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SessionLog
from engine.fatigue import RecentLogData


class SessionLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_today(self, user_id: int) -> SessionLog | None:
        result = await self.session.execute(
            select(SessionLog).where(
                SessionLog.user_id == user_id,
                SessionLog.date == date.today(),
            )
        )
        return result.scalar_one_or_none()

    async def get_yesterday(self, user_id: int) -> SessionLog | None:
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        result = await self.session.execute(
            select(SessionLog).where(
                SessionLog.user_id == user_id,
                SessionLog.date == yesterday,
            )
        )
        return result.scalar_one_or_none()

    async def get_unmarked_past(self, user_id: int) -> list[SessionLog]:
        """Past days (excluding today) where completion_status was never set."""
        result = await self.session.execute(
            select(SessionLog).where(
                SessionLog.user_id == user_id,
                SessionLog.completion_status.is_(None),
                SessionLog.date < date.today(),
            ).order_by(SessionLog.day_index.desc())
        )
        return list(result.scalars().all())

    async def delete_today(self, user_id: int) -> None:
        """Delete today's session log (used on progress reset)."""
        from sqlalchemy import delete
        await self.session.execute(
            delete(SessionLog).where(
                SessionLog.user_id == user_id,
                SessionLog.date == date.today(),
            )
        )
        await self.session.commit()

    async def get_or_create_today(self, user_id: int, day_index: int) -> tuple[SessionLog, bool]:
        log = await self.get_today(user_id)
        if log:
            return log, False
        log = SessionLog(user_id=user_id, date=date.today(), day_index=day_index)
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log, True

    async def update(self, log: SessionLog, **kwargs) -> SessionLog:
        for key, value in kwargs.items():
            setattr(log, key, value)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_recent(self, user_id: int, limit: int = 3) -> list[RecentLogData]:
        """Fetch recent completed days as RecentLogData for the fatigue detector."""
        result = await self.session.execute(
            select(SessionLog)
            .where(SessionLog.user_id == user_id, SessionLog.checkin_done == True)
            .order_by(SessionLog.date.desc())
            .limit(limit)
        )
        logs = list(result.scalars().all())
        return [
            RecentLogData(
                effort_level=log.effort_level,
                sleep_quality=log.sleep_quality or 2,
                completion_status=log.completion_status,
                wellbeing=log.wellbeing or 3,
                stress_level=log.stress_level or 1,
                pain_level=log.pain_level or 1,
            )
            for log in reversed(logs)  # oldest first
        ]

    async def completed_count(self, user_id: int) -> int:
        """Number of days marked as done or partial."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).where(
                SessionLog.user_id == user_id,
                SessionLog.completion_status.in_(["done", "partial"]),
            )
        )
        return result.scalar_one()

    async def streak(self, user_id: int) -> int:
        """
        Consecutive days the user engaged with the bot (did check-in).
        Counts backwards from today; breaks on the first calendar day with no check-in.
        Recovery / skipped / rest days all count as long as check-in was done.
        """
        from datetime import date, timedelta

        result = await self.session.execute(
            select(SessionLog.date)
            .where(SessionLog.user_id == user_id, SessionLog.checkin_done == True)
            .order_by(SessionLog.date.desc())
        )
        checkin_dates = {row[0] for row in result.fetchall()}

        count = 0
        expected = date.today()
        while expected in checkin_dates:
            count += 1
            expected -= timedelta(days=1)
        return count

    async def week_completion_rate(
        self, user_id: int, week_start_day: int, week_end_day: int
    ) -> float:
        """
        Completion rate for days in [week_start_day, week_end_day].
        done=1.0, partial=0.5, skipped=0.0, no record=0.0
        Returns float in [0.0, 1.0].
        """
        result = await self.session.execute(
            select(SessionLog).where(
                SessionLog.user_id == user_id,
                SessionLog.day_index >= week_start_day,
                SessionLog.day_index <= week_end_day,
                SessionLog.checkin_done == True,
            )
        )
        logs = list(result.scalars().all())

        total_days = week_end_day - week_start_day + 1
        score = 0.0
        for log in logs:
            if log.completion_status == "done":
                score += 1.0
            elif log.completion_status == "partial":
                score += 0.5
            # skipped or None → 0.0

        return score / total_days if total_days > 0 else 0.0

    async def get_logs_for_week(self, user_id: int, week_start_day: int, week_end_day: int) -> list[SessionLog]:
        result = await self.session.execute(
            select(SessionLog).where(
                SessionLog.user_id == user_id,
                SessionLog.day_index >= week_start_day,
                SessionLog.day_index <= week_end_day,
            ).order_by(SessionLog.day_index)
        )
        return list(result.scalars().all())

    async def pending_checkin_approvals(self, timeout_minutes: int = 60) -> list[SessionLog]:
        """Logs awaiting admin approval that have exceeded the timeout."""
        from datetime import datetime, timezone, timedelta
        from sqlalchemy.orm import joinedload
        from database.models import User
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        result = await self.session.execute(
            select(SessionLog)
            .join(SessionLog.user)
            .options(joinedload(SessionLog.user))
            .where(
                SessionLog.approval_pending == True,
                SessionLog.checkin_at <= cutoff,
            )
        )
        return list(result.scalars().all())

    async def pending_morning_reminder(self, utc_hour: int) -> list[SessionLog]:
        from sqlalchemy.orm import joinedload
        from database.models import User

        result = await self.session.execute(
            select(SessionLog)
            .join(SessionLog.user)
            .options(joinedload(SessionLog.user))
            .where(
                SessionLog.date == date.today(),
                SessionLog.morning_sent == False,
                SessionLog.checkin_done == False,
                User.reminders_enabled == True,
                ((utc_hour + User.timezone_offset) % 24) == User.morning_reminder_hour,
            )
        )
        return list(result.scalars().all())

    async def pending_evening_reminder(self, utc_hour: int) -> list[SessionLog]:
        """Returns ALL active users whose evening hour has come and reminder not yet sent."""
        from sqlalchemy.orm import joinedload
        from database.models import User

        result = await self.session.execute(
            select(SessionLog)
            .join(SessionLog.user)
            .options(joinedload(SessionLog.user))
            .where(
                SessionLog.date == date.today(),
                SessionLog.evening_sent == False,
                User.reminders_enabled == True,
                ((utc_hour + User.timezone_offset) % 24) == User.evening_reminder_hour,
            )
        )
        return list(result.scalars().all())
