from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.utils import safe_answer
from services.user_service import UserService
from texts import T

router = Router()


class ReminderStates(StatesGroup):
    choosing_morning_hour = State()
    choosing_evening_hour = State()


# ── Keyboards ──────────────────────────────────────────────────────────────────

def kb_reminders(enabled: bool, morning_hour: int, evening_hour: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_label = T.btn.reminders_enabled if enabled else T.btn.reminders_disabled
    builder.button(text=toggle_label, callback_data="rem:toggle")
    builder.button(text=T.btn.btn_morning.format(hour=morning_hour), callback_data="rem:set_morning")
    builder.button(text=T.btn.btn_evening.format(hour=evening_hour), callback_data="rem:set_evening")
    builder.adjust(1)
    return builder.as_markup()


def kb_hours(prefix: str) -> InlineKeyboardMarkup:
    """Hour selector: 5:00 – 23:00 in a 4-column grid."""
    builder = InlineKeyboardBuilder()
    for h in range(5, 24):
        builder.button(text=f"{h:02d}:00", callback_data=f"{prefix}:{h}")
    builder.adjust(4)
    return builder.as_markup()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _reminders_text(enabled: bool, morning_hour: int, evening_hour: int) -> str:
    status = T.reminders.status_enabled if enabled else T.reminders.status_disabled
    return T.reminders.menu_text.format(
        status=status,
        morning_hour=morning_hour,
        evening_hour=evening_hour,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:reminders")
async def cb_reminders_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user:
        return

    await callback.message.answer(
        _reminders_text(user.reminders_enabled, user.morning_reminder_hour, user.evening_reminder_hour),
        parse_mode="HTML",
        reply_markup=kb_reminders(user.reminders_enabled, user.morning_reminder_hour, user.evening_reminder_hour),
    )


# ── Toggle on/off ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "rem:toggle")
async def cb_toggle_reminders(callback: CallbackQuery, session: AsyncSession) -> None:
    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user:
        await safe_answer(callback)
        return

    new_state = not user.reminders_enabled
    await user_svc.update(user, reminders_enabled=new_state)
    await safe_answer(callback)

    await callback.message.edit_text(
        _reminders_text(new_state, user.morning_reminder_hour, user.evening_reminder_hour),
        parse_mode="HTML",
        reply_markup=kb_reminders(new_state, user.morning_reminder_hour, user.evening_reminder_hour),
    )


# ── Change morning hour ────────────────────────────────────────────────────────

@router.callback_query(F.data == "rem:set_morning")
async def cb_set_morning(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.set_state(ReminderStates.choosing_morning_hour)
    await callback.message.answer(T.reminders.ask_morning_hour, reply_markup=kb_hours("rem:morning"))


@router.callback_query(ReminderStates.choosing_morning_hour, F.data.startswith("rem:morning:"))
async def cb_morning_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    hour = int(callback.data.split(":")[2])
    await safe_answer(callback)
    await state.clear()
    await callback.message.edit_reply_markup()

    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    await user_svc.update(user, morning_reminder_hour=hour)

    await callback.message.answer(
        T.reminders.morning_set.format(hour=hour)
        + _reminders_text(user.reminders_enabled, hour, user.evening_reminder_hour),
        parse_mode="HTML",
        reply_markup=kb_reminders(user.reminders_enabled, hour, user.evening_reminder_hour),
    )


# ── Change evening hour ────────────────────────────────────────────────────────

@router.callback_query(F.data == "rem:set_evening")
async def cb_set_evening(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.set_state(ReminderStates.choosing_evening_hour)
    await callback.message.answer(T.reminders.ask_evening_hour, reply_markup=kb_hours("rem:evening"))


@router.callback_query(ReminderStates.choosing_evening_hour, F.data.startswith("rem:evening:"))
async def cb_evening_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    hour = int(callback.data.split(":")[2])
    await safe_answer(callback)
    await state.clear()
    await callback.message.edit_reply_markup()

    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    await user_svc.update(user, evening_reminder_hour=hour)

    await callback.message.answer(
        T.reminders.evening_set.format(hour=hour)
        + _reminders_text(user.reminders_enabled, user.morning_reminder_hour, hour),
        parse_mode="HTML",
        reply_markup=kb_reminders(user.reminders_enabled, user.morning_reminder_hour, hour),
    )
