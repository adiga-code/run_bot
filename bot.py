import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.engine import create_db, seed_workouts, session_maker
from database.middleware import DatabaseMiddleware
from database.whitelist_middleware import WhitelistMiddleware
from handlers import admin, checkin, onboarding, progress, reminders, start, workout
from scheduler.tasks import setup_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
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
