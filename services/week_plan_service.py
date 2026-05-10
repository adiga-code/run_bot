"""
services/week_plan_service.py
CRUD и бизнес-логика для WeekPlan / DayPlan.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import DayPlan, SessionLog, User, WeekPlan
from engine.week_planner import WeekBlueprint, build_week_plan, parse_available_weekdays
from engine.week_evaluator import WeekEvaluation, NextWeekDecision


def _monday(d: date) -> date:
    """Возвращает понедельник недели для даты d."""
    return d - timedelta(days=d.weekday())


def _sunday(d: date) -> date:
    """Возвращает воскресенье недели для даты d."""
    return _monday(d) + timedelta(days=6)


class WeekPlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Получение ─────────────────────────────────────────────────────────────

    async def get_current(self, user_id: int) -> WeekPlan | None:
        """Текущая активная WeekPlan (start_date <= сегодня <= end_date)."""
        today = date.today()
        result = await self.session.execute(
            select(WeekPlan)
            .options(selectinload(WeekPlan.days))
            .where(
                WeekPlan.user_id == user_id,
                WeekPlan.start_date <= today,
                WeekPlan.end_date >= today,
            )
        )
        return result.scalar_one_or_none()

    async def get_last(self, user_id: int) -> WeekPlan | None:
        """Последняя WeekPlan (по start_date убыванию)."""
        result = await self.session.execute(
            select(WeekPlan)
            .options(selectinload(WeekPlan.days))
            .where(WeekPlan.user_id == user_id)
            .order_by(WeekPlan.start_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_last_closed(self, user_id: int, limit: int = 8) -> list[WeekPlan]:
        """Последние закрытые недели (для evaluator / period_transitions)."""
        result = await self.session.execute(
            select(WeekPlan)
            .options(selectinload(WeekPlan.days))
            .where(
                WeekPlan.user_id == user_id,
                WeekPlan.closed_at.isnot(None),
            )
            .order_by(WeekPlan.start_date.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        return list(reversed(rows))  # от старых к новым

    async def get_last_successful(self, user_id: int) -> WeekPlan | None:
        """Последняя неделя с growth_eligible=True."""
        result = await self.session.execute(
            select(WeekPlan)
            .where(
                WeekPlan.user_id == user_id,
                WeekPlan.growth_eligible == True,
            )
            .order_by(WeekPlan.start_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_logs_for_week_plan(self, week_plan_id: int) -> list[SessionLog]:
        """Все SessionLog, привязанные к данной WeekPlan."""
        result = await self.session.execute(
            select(SessionLog).where(SessionLog.week_plan_id == week_plan_id)
        )
        return list(result.scalars().all())

    async def get_day_plan_for_today(self, user_id: int) -> DayPlan | None:
        """DayPlan для сегодняшнего дня (1=Пн..7=Вс)."""
        week_plan = await self.get_current(user_id)
        if not week_plan:
            return None
        today_dow = date.today().isoweekday()  # 1=Пн..7=Вс
        for dp in week_plan.days:
            if dp.day_of_week == today_dow:
                return dp
        return None

    # ── Создание ──────────────────────────────────────────────────────────────

    async def create_first_week(self, user: User, anchor_date: date | None = None) -> WeekPlan:
        """
        Создаёт первый WeekPlan сразу после одобрения тренером.
        start_date = ближайший понедельник от anchor_date (по умолч. сегодня).
        """
        anchor = anchor_date or date.today()
        start = _monday(anchor)
        if start < anchor:
            # Неделя уже началась — берём следующий понедельник
            start = start + timedelta(weeks=1)

        return await self._create_week(
            user=user,
            start_date=start,
            week_number=1,
            period=user.current_period or "base",
            period_week_number=1,
            target_minutes=user.weekly_target_minutes or 60,
            is_recovery_week=False,
            is_rollback_week=False,
        )

    async def create_for_next_week(self, user: User, decision: NextWeekDecision) -> WeekPlan:
        """Создаёт WeekPlan на следующую неделю по решению decide_next_week."""
        last = await self.get_last(user.telegram_id)
        if last:
            start = last.end_date + timedelta(days=1)
        else:
            start = _monday(date.today()) + timedelta(weeks=1)

        week_number = (user.program_week_number or 1) + 1
        period = decision.new_period or user.current_period or "base"
        pw_num = (user.period_week_number or 1) + 1
        if decision.new_period and decision.new_period != user.current_period:
            pw_num = 1  # переход → сбрасываем счётчик периода

        return await self._create_week(
            user=user,
            start_date=start,
            week_number=week_number,
            period=period,
            period_week_number=pw_num,
            target_minutes=decision.next_target_minutes,
            is_recovery_week=decision.is_recovery_week,
            is_rollback_week=decision.is_rollback,
        )

    async def _create_week(
        self,
        user: User,
        start_date: date,
        week_number: int,
        period: str,
        period_week_number: int,
        target_minutes: int,
        is_recovery_week: bool,
        is_rollback_week: bool,
    ) -> WeekPlan:
        """Внутренний метод: строит WeekPlan + DayPlan и сохраняет в БД."""
        available = parse_available_weekdays(user.available_weekdays)

        blueprint: WeekBlueprint = build_week_plan(
            user=user,
            week_number=week_number,
            period=period,
            target_minutes=target_minutes,
            is_recovery_week=is_recovery_week,
            available_weekdays=available,
        )

        week_plan = WeekPlan(
            user_id=user.telegram_id,
            week_number=week_number,
            cycle_number=user.cycle_number or 1,
            period=period,
            period_week_number=period_week_number,
            start_date=start_date,
            end_date=start_date + timedelta(days=6),
            weekly_target_minutes=target_minutes,
            is_recovery_week=is_recovery_week,
            is_rollback_week=is_rollback_week,
        )
        self.session.add(week_plan)
        await self.session.flush()  # получаем week_plan.id

        for slot in blueprint.days:
            dp = DayPlan(
                week_plan_id=week_plan.id,
                day_of_week=slot.day_of_week,
                day_type=slot.day_type,
                run_subtype=slot.run_subtype,
                planned_minutes=slot.planned_minutes,
                intensity=slot.intensity,
                is_key=slot.is_key,
            )
            self.session.add(dp)

        await self.session.commit()
        await self.session.refresh(week_plan)
        return week_plan

    # ── Закрытие недели ───────────────────────────────────────────────────────

    async def close_week(self, week_plan: WeekPlan, evaluation: WeekEvaluation) -> None:
        """Записывает итоги недели в WeekPlan."""
        week_plan.actual_running_minutes = evaluation.actual_minutes
        week_plan.completion_rate = round(evaluation.completion_rate, 4)
        week_plan.keys_completed = evaluation.keys_completed
        week_plan.growth_eligible = evaluation.growth_eligible
        week_plan.no_growth_reason = evaluation.no_growth_reason
        week_plan.closed_at = datetime.now(timezone.utc)

        # Обновляем is_key_completed в DayPlan
        logs_result = await self.session.execute(
            select(SessionLog).where(SessionLog.week_plan_id == week_plan.id)
        )
        logs = {log.day_of_week: log for log in logs_result.scalars().all() if log.day_of_week}

        for dp in week_plan.days:
            if dp.is_key:
                log = logs.get(dp.day_of_week)
                dp.is_key_completed = _calc_key_completed(dp, log)

        await self.session.commit()

    # ── Утилиты ───────────────────────────────────────────────────────────────

    def is_week_ending_today(self, week_plan: WeekPlan | None) -> bool:
        """True если сегодня воскресенье и это конец данной недели."""
        if not week_plan:
            return False
        return week_plan.end_date == date.today()


def _calc_key_completed(day_plan: DayPlan, log: SessionLog | None) -> bool:
    if not log or log.completion_status != "done":
        return False
    if log.assigned_version == "recovery":
        return False
    return True
