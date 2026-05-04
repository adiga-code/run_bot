import logging
from datetime import date, datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from keyboards.builders import kb_main_menu, kb_mark_workout, kb_absence_reason
from services.session_log_service import SessionLogService
from services.user_service import UserService
from services.workout_service import WorkoutService
from texts import T

logger = logging.getLogger(__name__)


async def _reactivate_extended_users(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Reactivates users with extended_week5=True who were marked 'completed' at day 35
    but still have days remaining in the extended 6-week program (up to day 42).
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
        completed_extended = result.scalars().all()
        for user in completed_extended:
            raw_day = (date.today() - user.program_start_date).days + 1
            if raw_day <= 42:
                await user_svc.update(user, status="active")
                # Create today's session log so the user gets their check-in today
                day = await user_svc.current_program_day(user)
                if day is not None:
                    await log_svc.get_or_create_today(user.telegram_id, day)
                logger.info(
                    "Auto-reactivated user %s for week 6 (day %d)",
                    user.telegram_id, raw_day,
                )
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "🏃 Твоя программа продолжается!\n\n"
                            "6-я неделя начинается — ты справился, и мы идём дальше. "
                            "Продолжай в том же темпе 💪"
                        ),
                        reply_markup=kb_main_menu(),
                    )
                except Exception:
                    pass


async def _create_daily_logs(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run at 00:05 UTC every day.
    Pre-create today's SessionLog for all active users.
    Marks users as 'completed' once the raw calendar day exceeds their program length,
    which stops all further reminders automatically.
    """
    # Reactivate completed extended users before processing active ones
    await _reactivate_extended_users(bot, session_maker)

    async with session_maker() as session:
        user_svc = UserService(session)
        log_svc = SessionLogService(session)

        # ── Process all active users ─────────────────────────────────────────────
        users = await user_svc.all_active()
        for user in users:
            if not user.program_start_date:
                continue
            max_day = user_svc._max_day(user)
            raw_day = (date.today() - user.program_start_date).days + 1
            if raw_day > max_day:
                await user_svc.update(user, status="completed")
                logger.info("User %s completed the program (day %d > %d)", user.telegram_id, raw_day, max_day)
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


async def _send_morning_reminders(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run every minute. Sends morning check-in reminders to users
    whose local hour matches their morning_reminder_hour.

    Если пользователь не проходил чекин ровно 3 дня — вместо обычного
    напоминания присылается сообщение «Что случилось?» с кнопками причин.
    """
    utc_hour = datetime.now(timezone.utc).hour

    async with session_maker() as session:
        log_svc = SessionLogService(session)
        logs = await log_svc.pending_morning_reminder(utc_hour)
        for log in logs:
            try:
                days_absent = await log_svc.days_since_last_checkin(log.user_id)
                if days_absent == 3:
                    # Ветка «3 дня без чекина» — вместо обычного напоминания
                    await bot.send_message(
                        chat_id=log.user_id,
                        text=T.scheduler.absence_3days,
                        reply_markup=kb_absence_reason(),
                    )
                else:
                    # Обычное утреннее напоминание
                    await bot.send_message(
                        chat_id=log.user_id,
                        text=T.scheduler.morning_reminder,
                        reply_markup=kb_main_menu(),
                    )
                await log_svc.update(log, morning_sent=True)
            except Exception:
                pass  # user blocked bot or other Telegram error — skip silently


async def _check_week_completion(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run at 23:55 UTC every day.
    For users whose calendar day is 7 or 14 (end of weeks 1 or 2),
    check weekly completion rate based on calendar dates.
    If < 75%, increment week_repeat_count so the next workout template
    repeats the same week — without moving the calendar day back.

    Week 3 (day 21) is NEVER repeated — all users automatically advance
    to week 4 (day 22+) regardless of completion rate.
    Week 4 (day 28) is the final week and is never repeated either.
    """
    from datetime import timedelta
    async with session_maker() as session:
        user_svc = UserService(session)
        log_svc = SessionLogService(session)
        users = await user_svc.all_active()
        for user in users:
            calendar_day = await user_svc.current_calendar_day(user)
            if calendar_day not in (7, 14):
                continue  # week repeats only apply to weeks 1 and 2

            # Date range for this calendar week
            week_end_date = user.program_start_date + timedelta(days=calendar_day - 1)
            week_start_date = week_end_date - timedelta(days=6)
            rate = await log_svc.week_completion_rate_by_dates(
                user.telegram_id, week_start_date, week_end_date
            )
            if rate < 0.75:
                await user_svc.update(user, week_repeat_count=user.week_repeat_count + 1)
                logger.info(
                    "User %s week completion %.0f%% < 75%% — repeating load week (repeat_count=%d)",
                    user.telegram_id, rate * 100, user.week_repeat_count,
                )


async def _send_evening_reminders(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run every minute. Sends evening message to ALL active users whose evening hour has come.
    Branches by completion status:
      - done/partial → support closing message
      - checkin done but no status → gentle reminder to mark
      - no checkin and no status → "day slipped, that's ok" message
    """
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
                # No checkin and no status
                text = T.scheduler.evening_missed
                markup = None

            try:
                await bot.send_message(
                    chat_id=log.user_id,
                    text=text,
                    reply_markup=markup,
                )
                await log_svc.update(log, evening_sent=True)
            except Exception:
                pass


async def _auto_approve_checkins(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run every minute. Auto-sends the bot's recommended workout to users whose
    check-in has been pending admin approval for more than 10 minutes.
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
                day_type = await wk_svc.get_day_type(user.level, log.day_index) or "run"

                if version == "rest":
                    await bot.send_message(
                        chat_id=log.user_id,
                        text=T.scheduler.rest_day,
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
                    "Auto-approved checkin for user %s → %s (timeout)",
                    log.user_id, version,
                )
            except Exception:
                logger.exception("Failed to auto-approve checkin for user %s", log.user_id)


def setup_scheduler(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIOScheduler:
    from datetime import datetime, timezone as tz
    scheduler = AsyncIOScheduler(timezone="UTC")

    # On startup: immediately reactivate completed extended users
    scheduler.add_job(
        _reactivate_extended_users,
        "date",
        run_date=datetime.now(tz.utc),
        args=[bot, session_maker],
        id="reactivate_extended_on_startup",
        replace_existing=True,
    )

    # Every minute: check who needs a morning reminder
    scheduler.add_job(
        _send_morning_reminders,
        CronTrigger(minute="*"),
        args=[bot, session_maker],
        id="morning_reminders",
        replace_existing=True,
    )

    # Every minute: check who needs an evening reminder
    scheduler.add_job(
        _send_evening_reminders,
        CronTrigger(minute="*"),
        args=[bot, session_maker],
        id="evening_reminders",
        replace_existing=True,
    )

    # Every minute: auto-send workout if admin hasn't approved in 10 min
    scheduler.add_job(
        _auto_approve_checkins,
        CronTrigger(minute="*"),
        args=[bot, session_maker],
        id="auto_approve_checkins",
        replace_existing=True,
    )

    # 00:05 UTC daily: pre-create logs for all active users; complete program if finished
    scheduler.add_job(
        _create_daily_logs,
        CronTrigger(hour=0, minute=5),
        args=[bot, session_maker],
        id="daily_log_creation",
        replace_existing=True,
    )

    # 23:55 UTC daily: check week completion; repeat week if < 75%
    scheduler.add_job(
        _check_week_completion,
        CronTrigger(hour=23, minute=55),
        args=[session_maker],
        id="week_completion_check",
        replace_existing=True,
    )

    return scheduler
