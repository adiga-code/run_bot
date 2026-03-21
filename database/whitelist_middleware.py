from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database.models import WhitelistEntry

# Commands and callback prefixes that are always accessible (no whitelist needed)
PUBLIC_COMMANDS = {"/start"}


def _get_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message):
        return event.from_user.id if event.from_user else None
    if isinstance(event, CallbackQuery):
        return event.from_user.id if event.from_user else None
    return None


def _get_text(event: TelegramObject) -> str:
    if isinstance(event, Message):
        return event.text or ""
    return ""


class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = _get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        # Admins always have access
        if user_id in settings.admin_ids:
            return await handler(event, data)

        text = _get_text(event)
        if text in PUBLIC_COMMANDS:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        result = await session.execute(
            select(WhitelistEntry).where(WhitelistEntry.telegram_id == user_id)
        )
        entry = result.scalar_one_or_none()

        if entry is None:
            if isinstance(event, Message):
                await event.answer(
                    "У вас нет доступа к этому боту.\n"
                    "Обратитесь к организатору программы для получения доступа."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Нет доступа.", show_alert=True)
            return

        return await handler(event, data)
