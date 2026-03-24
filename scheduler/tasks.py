from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from keyboards.builders import kb_main_menu, kb_mark_workout
from services.session_log_service import SessionLogService
from services.user_service import UserService


async def _create_daily_logs(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run at 00:05 UTC every day.
    Pre-create today's SessionLog for all active users.
    This ensures reminders can query logs by date without needing check-in first.
    """
    async with session_maker() as session:
        user_svc = UserService(session)
        log_svc = SessionLogService(session)
        users = await user_svc.all_active()
        for user in users:
            day = await user_svc.current_program_day(user)
            if day is not None and day <= 28:
                await log_svc.get_or_create_today(user.telegram_id, day)


async def _send_morning_reminders(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run every minute. Sends morning check-in reminders to users
    whose local hour matches their morning_reminder_hour.
    """
    utc_hour = datetime.now(timezone.utc).hour

    async with session_maker() as session:
        log_svc = SessionLogService(session)
        logs = await log_svc.pending_morning_reminder(utc_hour)
        for log in logs:
            try:
                await bot.send_message(
                    chat_id=log.user_id,
                    text=(
                        "🌅 Доброе утро!\n\n"
                        "Время пройти утренний чек-ин и узнать свою тренировку на сегодня.\n\n"
                        "Нажми /checkin или кнопку ниже 👇"
                    ),
                    reply_markup=kb_main_menu(),
                )
                await log_svc.update(log, morning_sent=True)
            except Exception:
                pass  # user blocked bot or other Telegram error — skip silently


async def _check_week_completion(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Run at 23:55 UTC every day.
    For users on day 7, 14, 21, or 28 (end of a week), check weekly completion rate.
    If < 75%, increment week_repeat_count so next day's index stays in the same week.
    """
    async with session_maker() as session:
        user_svc = UserService(session)
        log_svc = SessionLogService(session)
        users = await user_svc.all_active()
        for user in users:
            day = await user_svc.current_program_day(user)
            if day is None or day % 7 != 0:
                continue  # not end-of-week today
            week_start, week_end = user_svc.current_week_range(day)
            rate = await log_svc.week_completion_rate(user.telegram_id, week_start, week_end)
            if rate < 0.75:
                await user_svc.update(user, week_repeat_count=user.week_repeat_count + 1)


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
                text = (
                    "🌙 Отличный день!\n\n"
                    "Тренировка выполнена — это и есть прогресс. "
                    "Дай телу восстановиться до завтра 💪"
                )
                markup = None
            elif status == "partial":
                text = (
                    "🌙 Хорошая работа!\n\n"
                    "Частичная тренировка — тоже движение вперёд. "
                    "Завтра продолжаем 🙌"
                )
                markup = None
            elif checkin_done and not status:
                text = (
                    "🌙 Напоминание!\n\n"
                    "Ты сегодня занимался(ась)? Отметь результат — "
                    "это помогает отслеживать твой прогресс 👇"
                )
                markup = kb_mark_workout()
            else:
                # No checkin and no status
                text = (
                    "🌙 Похоже, сегодня выпал день — ничего страшного.\n\n"
                    "Завтра возвращаемся в ритм 🙌"
                )
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


def setup_scheduler(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

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

    # 00:05 UTC daily: pre-create logs for all active users
    scheduler.add_job(
        _create_daily_logs,
        CronTrigger(hour=0, minute=5),
        args=[session_maker],
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
