"""
scheduler/tasks.py
Периодические задачи бота (APScheduler).

Поддерживает две системы параллельно:
  • Старая 28-дневная  — user.current_period is None
  • Новая цикловая     — user.current_period is not None
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import settings
from keyboards.builders import kb_absence_reason, kb_completion_v2, kb_main_menu, kb_mark_workout
from services.session_log_service import SessionLogService
from services.user_service import UserService
from services.workout_service import WorkoutService
from texts import T

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# _reactivate_extended_users  (только старая система — без изменений)
# ══════════════════════════════════════════════════════════════════════════════

async def _reactivate_extended_users(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Reactivates users with extended_week5=True who were marked 'completed' early
    but still have days remaining in the extended program (up to day 42).
    Runs once on bot startup and then nightly as part of _create_daily_logs.
    """
    from sqlalchemy import select as sa_select
    from database.models import User

    async with session_maker() as session:
        user_svc = UserService(session)
        result = await session.execute(
            sa_select(User).where(
                User.status == "completed",
                User.extended_week5 == True,
                User.program_start_date.isnot(None),
            )
        )
        log_svc = SessionLogService(session)
        for user in result.scalars().all():
            raw_day = (date.today() - user.program_start_date).days + 1
            max_day = user_svc._max_day(user)
            if raw_day <= max_day:
                await user_svc.update(user, status="active")
                day = await user_svc.current_program_day(user)
                if day is not None:
                    await log_svc.get_or_create_today(user.telegram_id, day)
                logger.info(
                    "Auto-reactivated user %s (day %d / %d)",
                    user.telegram_id, raw_day, max_day,
                )
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "🏃 Твоя программа продолжается!\n\n"
                            "Продолжай в том же темпе 💪"
                        ),
                        reply_markup=kb_main_menu(),
                    )
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
# _create_daily_logs  (обе системы)
# ══════════════════════════════════════════════════════════════════════════════

async def _create_daily_logs(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    00:05 UTC ежедневно.
    • Старая система: создаёт SessionLog(day_index=...) для всех активных пользователей.
    • Новая система: создаёт SessionLog(week_plan_id=..., day_plan_id=...) для дней,
      у которых есть DayPlan на сегодня в текущем WeekPlan.
    """
    await _reactivate_extended_users(bot, session_maker)

    async with session_maker() as session:
        user_svc = UserService(session)
        log_svc = SessionLogService(session)
        users = await user_svc.all_active()

        for user in users:
            try:
                if user.current_period is not None:
                    # ── Новая цикловая система ────────────────────────────────
                    await _create_log_new_system(session, log_svc, user)
                else:
                    # ── Старая 28-дневная система ─────────────────────────────
                    if not user.program_start_date:
                        continue
                    max_day = user_svc._max_day(user)
                    raw_day = (date.today() - user.program_start_date).days + 1
                    if raw_day > max_day:
                        await user_svc.update(user, status="completed")
                        logger.info(
                            "User %s completed the program (day %d > %d)",
                            user.telegram_id, raw_day, max_day,
                        )
                        try:
                            await bot.send_message(
                                chat_id=user.telegram_id,
                                text=(
                                    "🎉 Программа завершена!\n\n"
                                    "Ты прошёл все {} дней — это большой результат. "
                                    "Тренер свяжется с тобой по поводу дальнейших шагов 💪"
                                ).format(max_day),
                                reply_markup=kb_main_menu(),
                            )
                        except Exception:
                            pass
                    else:
                        day = await user_svc.current_program_day(user)
                        if day is not None:
                            await log_svc.get_or_create_today(user.telegram_id, day)
            except Exception:
                logger.exception("Error creating daily log for user %s", user.telegram_id)


async def _create_log_new_system(
    session: AsyncSession,
    log_svc: SessionLogService,
    user,
) -> None:
    """
    Создаёт SessionLog для нового дня в новой цикловой системе.
    Пропускает дни без DayPlan (пользователь не тренируется).
    """
    from database.models import SessionLog
    from services.week_plan_service import WeekPlanService

    wk_svc = WeekPlanService(session)
    week_plan = await wk_svc.get_current(user.telegram_id)
    if not week_plan:
        return  # план ещё не создан — ждём тренера

    today_dow = date.today().isoweekday()  # 1=Пн..7=Вс
    day_plan = next(
        (dp for dp in week_plan.days if dp.day_of_week == today_dow), None
    )
    if not day_plan:
        return  # сегодня не тренировочный день

    existing = await log_svc.get_today(user.telegram_id)
    if existing:
        return  # уже создан

    log = SessionLog(
        user_id=user.telegram_id,
        date=date.today(),
        day_index=0,  # не используется в новой системе
        week_plan_id=week_plan.id,
        day_plan_id=day_plan.id,
        day_of_week=today_dow,
        planned_minutes=day_plan.planned_minutes,
    )
    session.add(log)
    await session.commit()
    logger.debug(
        "Created new-system SessionLog for user %s, day_of_week=%d", user.telegram_id, today_dow
    )


# ══════════════════════════════════════════════════════════════════════════════
# _send_morning_reminders  (без изменений)
# ══════════════════════════════════════════════════════════════════════════════

async def _send_morning_reminders(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Каждую минуту. Отправляет утреннее напоминание тем пользователям,
    чей morning_reminder_hour совпал с текущим UTC часом.
    """
    utc_hour = datetime.now(timezone.utc).hour

    async with session_maker() as session:
        log_svc = SessionLogService(session)
        logs = await log_svc.pending_morning_reminder(utc_hour)
        for log in logs:
            try:
                days_absent = await log_svc.days_since_last_checkin(log.user_id)
                if days_absent == 3:
                    await bot.send_message(
                        chat_id=log.user_id,
                        text=T.scheduler.absence_3days,
                        reply_markup=kb_absence_reason(),
                    )
                else:
                    await bot.send_message(
                        chat_id=log.user_id,
                        text=T.scheduler.morning_reminder,
                        reply_markup=kb_main_menu(),
                    )
                await log_svc.update(log, morning_sent=True)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# _check_week_completion  (обе системы)
# ══════════════════════════════════════════════════════════════════════════════

async def _check_week_completion(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    23:55 UTC ежедневно.

    Старая система:
      calendar_day 7 или 14 → если < 75% выполнения, week_repeat_count + 1.

    Новая система:
      Если сегодня конец текущей WeekPlan (воскресенье, week_plan.end_date == today):
        1. evaluate_week
        2. Обработать red_flag (triggers_rollback)
        3. decide_next_week + period_transitions
        4. Закрыть текущую неделю
        5. Создать следующую WeekPlan
    """
    from datetime import timedelta

    async with session_maker() as session:
        user_svc = UserService(session)
        log_svc = SessionLogService(session)
        users = await user_svc.all_active()

        for user in users:
            try:
                if user.current_period is not None:
                    await _check_week_new_system(session, user_svc, user)
                else:
                    # ── Старая система ────────────────────────────────────────
                    calendar_day = await user_svc.current_calendar_day(user)
                    if calendar_day not in (7, 14):
                        continue
                    week_end_date = user.program_start_date + timedelta(days=calendar_day - 1)
                    week_start_date = week_end_date - timedelta(days=6)
                    rate = await log_svc.week_completion_rate_by_dates(
                        user.telegram_id, week_start_date, week_end_date
                    )
                    if rate < 0.75:
                        await user_svc.update(
                            user, week_repeat_count=user.week_repeat_count + 1
                        )
                        logger.info(
                            "User %s week completion %.0f%% < 75%% — repeating (count=%d)",
                            user.telegram_id, rate * 100, user.week_repeat_count,
                        )
            except Exception:
                logger.exception("Error in week completion check for user %s", user.telegram_id)


async def _check_week_new_system(
    session: AsyncSession,
    user_svc: UserService,
    user,
) -> None:
    """
    Закрывает текущую неделю и создаёт следующую для нового пользователя.
    Вызывается только если сегодня конец WeekPlan (end_date == today).
    """
    from engine.week_evaluator import WeekEvaluation, evaluate_week, decide_next_week
    from engine.period_transitions import (
        check_period_transition, check_cycle_end, start_new_cycle,
    )
    from services.week_plan_service import WeekPlanService

    wk_svc = WeekPlanService(session)
    week_plan = await wk_svc.get_current(user.telegram_id)

    if not week_plan:
        return

    # Проверяем что неделя заканчивается сегодня
    if week_plan.end_date != date.today():
        return

    # ── Получаем логи для этой недели ────────────────────────────────────────
    logs = await wk_svc.get_logs_for_week_plan(week_plan.id)

    # ── Оцениваем ─────────────────────────────────────────────────────────────
    evaluation = evaluate_week(week_plan, logs)

    # ── Red flag: 3 дня подряд с болью 3 ─────────────────────────────────────
    if evaluation.triggers_rollback and not getattr(user, "red_flag_active", False):
        await user_svc.update(
            user,
            red_flag_active=True,
            red_flag_reason="3 дня подряд с болью (6–10/10)",
            red_flag_at=datetime.now(timezone.utc),
        )
        for admin_id in settings.admin_ids:
            try:
                from aiogram import Bot as _Bot  # noqa: F401 — bot не нужен здесь
                pass  # Bot недоступен здесь — уведомление придёт через следующий чек-ин
            except Exception:
                pass
        logger.warning(
            "Red flag set for user %s (3-day high-pain streak)", user.telegram_id
        )

    # ── Конец цикла? ──────────────────────────────────────────────────────────
    cycle_ended = check_cycle_end(user, evaluation)

    if cycle_ended:
        await _handle_cycle_end(session, user_svc, wk_svc, user, week_plan, evaluation)
        return

    # ── Получаем историю закрытых недель для проверки перехода периодов ───────
    recent_closed = await wk_svc.get_last_closed(user.telegram_id, limit=8)
    recent_evals_mock = [
        WeekEvaluation(
            completion_rate=w.completion_rate or 0.0,
            keys_completed=w.keys_completed if w.keys_completed is not None else True,
            had_high_pain=False,
            high_pain_streak=0,
            mild_pain_streak=0,
            light_days=0,
            recovery_days=0,
            actual_minutes=w.actual_running_minutes or 0,
            growth_eligible=w.growth_eligible if w.growth_eligible is not None else False,
            no_growth_reason=w.no_growth_reason,
            triggers_rollback=False,
        )
        for w in recent_closed
    ]
    all_evals = recent_evals_mock + [evaluation]

    # ── Переход периода ────────────────────────────────────────────────────────
    new_period = check_period_transition(user, recent_closed, all_evals)

    # ── Решение по следующей неделе ────────────────────────────────────────────
    decision = decide_next_week(user, week_plan, evaluation)
    if new_period:
        decision.new_period = new_period

    # ── Обновляем счётчики пользователя ──────────────────────────────────────
    growth_streak = user.growth_streak or 0
    weeks_since_recovery = user.weeks_since_recovery or 0

    if decision.is_recovery_week:
        growth_streak = 0
        weeks_since_recovery = 0
    elif evaluation.growth_eligible:
        growth_streak += 1
        weeks_since_recovery += 1
    else:
        growth_streak = 0
        weeks_since_recovery += 1

    peak = max(user.peak_volume_minutes or 0, evaluation.actual_minutes)
    mac_peak = max(user.macrocycle_peak_volume or 0, evaluation.actual_minutes)

    update_kwargs: dict = {
        "growth_streak": growth_streak,
        "weeks_since_recovery": weeks_since_recovery,
        "program_week_number": (user.program_week_number or 1) + 1,
        "peak_volume_minutes": peak,
        "macrocycle_peak_volume": mac_peak,
        "weekly_target_minutes": decision.next_target_minutes,
    }
    if new_period:
        update_kwargs["current_period"] = new_period
        update_kwargs["period_week_number"] = 1
    else:
        update_kwargs["period_week_number"] = (user.period_week_number or 1) + 1

    if evaluation.growth_eligible:
        update_kwargs["last_successful_volume"] = evaluation.actual_minutes

    await user_svc.update(user, **update_kwargs)

    # ── Закрываем текущую неделю ───────────────────────────────────────────────
    await wk_svc.close_week(week_plan, evaluation)

    # ── Создаём следующую WeekPlan ────────────────────────────────────────────
    # Перечитываем пользователя после update
    user = await user_svc.get_or_raise(user.telegram_id)
    await wk_svc.create_for_next_week(user, decision)

    logger.info(
        "Week %d closed for user %s: rate=%.0f%% eligible=%s → next=%d min %s",
        week_plan.week_number,
        user.telegram_id,
        evaluation.completion_rate * 100,
        evaluation.growth_eligible,
        decision.next_target_minutes,
        f"[period→{new_period}]" if new_period else "",
    )


async def _handle_cycle_end(
    session: AsyncSession,
    user_svc: UserService,
    wk_svc,
    user,
    week_plan,
    evaluation,
) -> None:
    """Закрывает цикл и запускает следующий автоматически."""
    from engine.period_transitions import start_new_cycle
    from engine.week_evaluator import evaluate_week  # noqa — already called before

    # Закрываем неделю
    await wk_svc.close_week(week_plan, evaluation)

    # Определяем режим нового цикла
    growth_streak = user.growth_streak or 0
    level = user.level or 1
    if level < 3 and growth_streak >= 3:
        mode = "advance"
    elif growth_streak > 0:
        mode = "stay"
    else:
        mode = "redo"

    new_cycle_params = start_new_cycle(user, mode)
    await user_svc.update(user, **new_cycle_params)

    # Перечитываем и создаём первую неделю нового цикла
    user = await user_svc.get_or_raise(user.telegram_id)
    from services.week_plan_service import WeekPlanService
    wk = WeekPlanService(session)
    await wk.create_first_week(user)

    logger.info(
        "Cycle ended for user %s (level %d) → mode=%s → new cycle %d",
        user.telegram_id, level, mode, user.cycle_number or 1,
    )


# ══════════════════════════════════════════════════════════════════════════════
# _send_evening_reminders  (без изменений)
# ══════════════════════════════════════════════════════════════════════════════

async def _send_evening_reminders(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Каждую минуту. Вечерние напоминания по completion_status."""
    utc_hour = datetime.now(timezone.utc).hour

    async with session_maker() as session:
        log_svc = SessionLogService(session)
        logs = await log_svc.pending_evening_reminder(utc_hour)
        for log in logs:
            status = log.completion_status
            checkin_done = log.checkin_done

            if status == "done":
                text = T.scheduler.evening_done
                markup = None
            elif status == "partial":
                text = T.scheduler.evening_partial
                markup = None
            elif checkin_done and not status:
                text = T.scheduler.evening_reminder
                markup = kb_mark_workout()
            else:
                text = T.scheduler.evening_missed
                markup = None

            try:
                await bot.send_message(chat_id=log.user_id, text=text, reply_markup=markup)
                await log_svc.update(log, evening_sent=True)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# _auto_approve_checkins  (обе системы)
# ══════════════════════════════════════════════════════════════════════════════

async def _auto_approve_checkins(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Каждую минуту. Автоматически отправляет рекомендованную тренировку,
    если тренер не одобрил чек-ин в течение 10 минут.
    """
    async with session_maker() as session:
        from handlers.utils import send_workout_to_user
        log_svc = SessionLogService(session)
        wk_svc = WorkoutService(session)
        user_svc = UserService(session)

        logs = await log_svc.pending_checkin_approvals(timeout_minutes=10)
        for log in logs:
            try:
                user = log.user
                version = log.assigned_version or "light"

                if user.current_period is not None:
                    # ── Новая цикловая система ────────────────────────────────
                    await _auto_send_new_system(bot, session, log_svc, user, log, version)
                else:
                    # ── Старая система ────────────────────────────────────────
                    day_type = await wk_svc.get_day_type(user.level, log.day_index) or "run"
                    if version == "rest":
                        await bot.send_message(
                            chat_id=log.user_id,
                            text=T.checkin.rest_day,
                            reply_markup=kb_main_menu(),
                        )
                    else:
                        workout = await wk_svc.get(
                            user.level, log.day_index, version,
                            strength_format=user.strength_format if day_type == "strength" else None,
                        )
                        if workout:
                            await send_workout_to_user(
                                bot, log.user_id, log.day_index,
                                workout, day_type, version, user.strength_format, user.level,
                                calendar_day=user_svc.log_calendar_day(user, log),
                            )

                await log_svc.update(log, approval_pending=False)
                logger.info(
                    "Auto-approved checkin for user %s → %s (timeout)", log.user_id, version
                )
            except Exception:
                logger.exception("Failed to auto-approve checkin for user %s", log.user_id)


async def _auto_send_new_system(
    bot: Bot,
    session: AsyncSession,
    log_svc: SessionLogService,
    user,
    log,
    version: str,
) -> None:
    """
    Auto-sends workout to new-system user after 10-minute approval timeout.
    Mirrors _approve_checkin_new in admin.py.
    """
    from datetime import date as date_cls
    from sqlalchemy import select as sa_select
    from database.models import DayPlan, WeekPlan, WorkoutTemplate
    from engine.workout_renderer import (
        render_run_workout, render_strength_from_template, RenderedWorkout,
    )
    from texts import T

    if version == "rest":
        await bot.send_message(
            chat_id=log.user_id,
            text=T.checkin.rest_day,
            reply_markup=kb_main_menu(),
        )
        return

    day_type = "run"
    run_subtype = None
    if log.day_plan_id:
        dp_res = await session.execute(
            sa_select(DayPlan).where(DayPlan.id == log.day_plan_id)
        )
        dp = dp_res.scalar_one_or_none()
        if dp:
            day_type = dp.day_type
            run_subtype = dp.run_subtype

    week_plan = None
    if log.week_plan_id:
        wp_res = await session.execute(
            sa_select(WeekPlan).where(WeekPlan.id == log.week_plan_id)
        )
        week_plan = wp_res.scalar_one_or_none()

    target_minutes = log.planned_minutes or user.weekly_target_minutes or 30
    level = user.level or 1
    period = week_plan.period if week_plan else user.current_period

    if day_type == "run":
        rendered = render_run_workout(
            run_subtype=run_subtype or "easy",
            target_minutes=target_minutes,
            version=version,
            level=level,
            period=period,
            long_stage=2 if getattr(user, "l1_long_independent", False) else 1,
        )
    elif day_type == "strength":
        tmpl = None
        for period_filter in (period, None):
            q = sa_select(WorkoutTemplate).where(
                WorkoutTemplate.level == level,
                WorkoutTemplate.day_type == "strength",
                WorkoutTemplate.version == version,
            )
            if period_filter is not None:
                q = q.where(WorkoutTemplate.period == period_filter)
            else:
                q = q.where(WorkoutTemplate.period.is_(None))
            if user.strength_format:
                q = q.where(WorkoutTemplate.strength_format == user.strength_format)
            res = await session.execute(q.limit(1))
            tmpl = res.scalar_one_or_none()
            if tmpl:
                break
        if tmpl:
            rendered = render_strength_from_template(tmpl, target_minutes, version)
        else:
            rendered = RenderedWorkout(
                title="Силовая тренировка",
                text=T.checkin.no_template_fallback,
                planned_minutes=target_minutes,
                version=version,
            )
    else:
        rendered = RenderedWorkout(
            title="Тренировка",
            text=T.checkin.no_template_fallback,
            planned_minutes=target_minutes,
            version=version,
        )

    dow = log.day_of_week or date_cls.today().isoweekday()
    week_num = user.program_week_number or 1
    header = T.checkin.workout_header_new.format(
        week=week_num, dow=dow, title=rendered.title,
    )
    await bot.send_message(
        chat_id=log.user_id,
        text=header + "\n\n" + rendered.text,
        parse_mode="HTML",
        reply_markup=kb_completion_v2(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# setup_scheduler
# ══════════════════════════════════════════════════════════════════════════════

def setup_scheduler(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIOScheduler:
    from datetime import datetime, timezone as tz
    scheduler = AsyncIOScheduler(timezone="UTC")

    # На старте: сразу реактивировать завершивших extended пользователей
    scheduler.add_job(
        _reactivate_extended_users,
        "date",
        run_date=datetime.now(tz.utc),
        args=[bot, session_maker],
        id="reactivate_extended_on_startup",
        replace_existing=True,
    )

    # Каждую минуту: утренние напоминания
    scheduler.add_job(
        _send_morning_reminders,
        CronTrigger(minute="*"),
        args=[bot, session_maker],
        id="morning_reminders",
        replace_existing=True,
    )

    # Каждую минуту: вечерние напоминания
    scheduler.add_job(
        _send_evening_reminders,
        CronTrigger(minute="*"),
        args=[bot, session_maker],
        id="evening_reminders",
        replace_existing=True,
    )

    # Каждую минуту: авто-одобрение чек-инов через 10 минут
    scheduler.add_job(
        _auto_approve_checkins,
        CronTrigger(minute="*"),
        args=[bot, session_maker],
        id="auto_approve_checkins",
        replace_existing=True,
    )

    # 00:05 UTC: создать логи дня для всех активных пользователей
    scheduler.add_job(
        _create_daily_logs,
        CronTrigger(hour=0, minute=5),
        args=[bot, session_maker],
        id="daily_log_creation",
        replace_existing=True,
    )

    # 23:55 UTC: проверка завершения недели (обе системы)
    scheduler.add_job(
        _check_week_completion,
        CronTrigger(hour=23, minute=55),
        args=[session_maker],
        id="week_completion_check",
        replace_existing=True,
    )

    return scheduler
