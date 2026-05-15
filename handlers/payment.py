"""Payment handlers — plan selection, payment link, status check."""
from __future__ import annotations

import logging

import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Payment, User
from engine.access import PLAN_PRICES, get_access_status, trial_days_left

logger = logging.getLogger(__name__)
router = Router()

ADMIN_BACKEND = settings.admin_backend_url  # e.g. "http://backend:8000"


def _plan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📅 Месяц — {PLAN_PRICES['monthly']} ₽ (28 дней)",
            callback_data="pay:plan:monthly",
        )],
        [InlineKeyboardButton(
            text=f"🔥 Год — {PLAN_PRICES['annual']} ₽ (365 дней)",
            callback_data="pay:plan:annual",
        )],
    ])


def _check_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"pay:check:{payment_id}")],
        [InlineKeyboardButton(text="💳 Другой план", callback_data="pay:choose_plan")],
    ])


@router.callback_query(lambda c: c.data == "pay:choose_plan")
async def cb_choose_plan(call: CallbackQuery) -> None:
    await call.message.answer(
        "Выберите план доступа к программе:",
        reply_markup=_plan_keyboard(),
    )
    await call.answer()


@router.callback_query(lambda c: (c.data or "").startswith("pay:plan:"))
async def cb_select_plan(call: CallbackQuery, session: AsyncSession) -> None:
    plan_type = call.data.split(":")[-1]  # monthly / annual
    if plan_type not in PLAN_PRICES:
        await call.answer("Неизвестный план", show_alert=True)
        return

    await call.answer("Создаём платёж…")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{ADMIN_BACKEND}/api/payments/create",
                json={"user_id": call.from_user.id, "plan_type": plan_type},
                headers={"X-Internal-Token": settings.internal_token},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("Payment create error: %s", e)
        await call.message.answer("Ошибка создания платежа. Попробуйте позже.")
        return

    payment_url = data["payment_url"]
    payment_id = data["payment_id"]
    amount = PLAN_PRICES[plan_type]
    plan_label = "28 дней" if plan_type == "monthly" else "365 дней"

    await call.message.answer(
        f"💳 Оплата доступа к программе\n\n"
        f"План: {'Месяц' if plan_type == 'monthly' else 'Год'} ({plan_label})\n"
        f"Сумма: {amount} ₽\n\n"
        f"👉 <a href=\"{payment_url}\">Перейти к оплате</a>\n\n"
        "После оплаты нажмите кнопку ниже:",
        reply_markup=_check_keyboard(payment_id),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: (c.data or "").startswith("pay:check:"))
async def cb_check_payment(call: CallbackQuery, session: AsyncSession) -> None:
    payment_id = int(call.data.split(":")[-1])
    await call.answer("Проверяем платёж…")

    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()

    if payment is None:
        await call.message.answer("Платёж не найден.")
        return

    if payment.status == "succeeded":
        await call.message.answer(
            "✅ Оплата подтверждена! Доступ к программе открыт.\n"
            "Продолжайте тренировки 🏃"
        )
        return

    # Re-check with backend
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{ADMIN_BACKEND}/api/payments/{payment_id}/status",
                headers={"X-Internal-Token": settings.internal_token},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("Payment status check error: %s", e)
        await call.message.answer("Не удалось проверить. Попробуйте через минуту.")
        return

    if data["status"] == "succeeded":
        await call.message.answer(
            "✅ Оплата подтверждена! Доступ открыт.\n"
            "Продолжайте тренировки 🏃"
        )
    else:
        await call.message.answer(
            "⏳ Платёж ещё не поступил.\n"
            "Проверьте оплату и нажмите кнопку снова через минуту.",
            reply_markup=_check_keyboard(payment_id),
        )
