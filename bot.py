import asyncio
import logging
import logging.handlers
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.engine import create_db, seed_workouts, session_maker
from database.middleware import DatabaseMiddleware
from database.whitelist_middleware import WhitelistMiddleware
from handlers import admin, checkin, onboarding, progress, reminders, start, workout
from scheduler.tasks import setup_scheduler

# Ensure logs directory exists
_LOGS_DIR = "/app/logs"
os.makedirs(_LOGS_DIR, exist_ok=True)

# Root logger: console + rotating file
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)

_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)
_root_logger.addHandler(_console_handler)

_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_LOGS_DIR, "bot.log"),
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)
_root_logger.addHandler(_file_handler)

logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware chain (order matters)
    dp.update.middleware(DatabaseMiddleware(session_maker))   # 1. inject session
    dp.update.middleware(WhitelistMiddleware())               # 2. check access

    # Routers (registration order = handler priority)
    dp.include_router(admin.router)       # admin commands first (no FSM conflicts)
    dp.include_router(start.router)
    dp.include_router(onboarding.router)
    dp.include_router(checkin.router)
    dp.include_router(workout.router)
    dp.include_router(reminders.router)
    dp.include_router(progress.router)

    # DB init
    await create_db()
    await seed_workouts()

    # Scheduler
    scheduler = setup_scheduler(bot, session_maker)
    scheduler.start()
    logger.info("Scheduler started")

    # Drop pending updates and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
