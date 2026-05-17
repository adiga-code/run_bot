"""AccessMiddleware — blocks expired users, shows payment prompt."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from engine.access import get_access_status, trial_days_left

# Commands / callbacks always allowed regardless of payment status
_ALWAYS_ALLOWED_COMMANDS = {"/start"}
_ALWAYS_ALLOWED_PREFIXES = ("pay:", "payment:", "mat:")


def _is_allowed_without_payment(event: TelegramObject) -> bool:
    if isinstance(event, Message):
        text = event.text or ""
        return text in _ALWAYS_ALLOWED_COMMANDS
    if isinstance(event, CallbackQuery):
        data = event.data or ""
        return any(data.startswith(p) for p in _ALWAYS_ALLOWED_PREFIXES)
    return False


def _payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="pay:choose_plan"),
    ]])


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Admins bypass access check
        if user_id in settings.admin_ids:
            return await handler(event, data)

        # Always allow payment-related interactions
        if _is_allowed_without_payment(event):
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if session is None:
            return await handler(event, data)

        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            return await handler(event, data)

        # Allow non-complete onboarding through
        if not user.onboarding_complete:
            return await handler(event, data)

        # User finished onboarding but awaiting admin decision (trial or payment)
        if user.status == "pending":
            if isinstance(event, Message):
                await event.answer("⏳ Ваша заявка на рассмотрении. Мы скоро свяжемся с вами!")
            elif isinstance(event, CallbackQuery):
                await event.answer("Ждём одобрения заявки", show_alert=True)
            return

        status = get_access_status(user)

        if status == "trial_warning":
            days = trial_days_left(user)
            if isinstance(event, Message):
                await event.answer(
                    f"⚠️ Пробный период заканчивается — осталось {days} {_days_word(days)}.\n"
                    "Оплатите доступ, чтобы продолжить без перерыва.",
                    reply_markup=_payment_keyboard(),
                )
            return await handler(event, data)

        if status == "expired":
            text = (
                "🔒 Ваш пробный период завершён.\n\n"
                "Чтобы продолжить тренировки, оплатите доступ к программе."
            )
            kb = _payment_keyboard()
            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb)
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ истёк", show_alert=True)
                await event.message.answer(text, reply_markup=kb)
            return  # block handler

        return await handler(event, data)


def _days_word(n: int) -> str:
    if n == 1:
        return "день"
    if 2 <= n <= 4:
        return "дня"
    return "дней"
