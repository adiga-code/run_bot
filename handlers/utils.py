import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


async def safe_answer(callback: CallbackQuery, text: str = "", show_alert: bool = False) -> None:
    """Answer a callback query, silently ignoring expired-query errors."""
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as e:
        if "query is too old" in str(e) or "query ID is invalid" in str(e):
            logger.warning("Expired callback query %s ignored", callback.id)
        else:
            raise
