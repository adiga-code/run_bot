"""
handlers/absence.py — обработка ветки «3 дня без чекина».

Флоу:
  1. Планировщик присылает сообщение «Мы заметили, что ты не занимался уже 3 дня».
  2. Пользователь выбирает причину (6 вариантов).
  3. Бот отвечает поддерживающим текстом.
  4. Для причин «нет времени», «мотивация», «погода» — через 5 минут:
       «Ну что, сделаем тренировку? Да/Нет»
     • Да  → запускаем чекин
     • Нет → «Окей, возвращайся…»
  5. Для «усталость», «болею», «другое» — ждём ещё 3 дня (бот молчит,
     утренние напоминания возобновятся автоматически на следующий день).
"""

import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.utils import safe_answer
from keyboards.builders import kb_main_menu, kb_return_training
from texts import T

logger = logging.getLogger(__name__)

router = Router()


class AbsenceStates(StatesGroup):
    waiting_custom_reason = State()


# ── Причины отсутствия ────────────────────────────────────────────────────────

@router.callback_query(F.data == "absence:tired")
async def absence_tired(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(T.scheduler.absence_tired_resp)
    # Для «устал» — просто поддержка, без follow-up вопроса


@router.callback_query(F.data == "absence:no_time")
async def absence_no_time(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(T.scheduler.absence_no_time_resp)
    # Через 5 минут спрашиваем про тренировку
    asyncio.create_task(_delayed_return_question(callback.bot, callback.from_user.id))


@router.callback_query(F.data == "absence:motivation")
async def absence_motivation(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(T.scheduler.absence_motivation_resp)
    asyncio.create_task(_delayed_return_question(callback.bot, callback.from_user.id))


@router.callback_query(F.data == "absence:sick")
async def absence_sick(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(T.scheduler.absence_sick_resp)
    # Для «болею» — просто поддержка, без follow-up вопроса


@router.callback_query(F.data == "absence:weather")
async def absence_weather(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(T.scheduler.absence_weather_resp)
    asyncio.create_task(_delayed_return_question(callback.bot, callback.from_user.id))


@router.callback_query(F.data == "absence:other")
async def absence_other(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(AbsenceStates.waiting_custom_reason)
    await callback.message.answer(T.scheduler.absence_other_ask)


@router.message(AbsenceStates.waiting_custom_reason)
async def absence_custom_reason(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(T.scheduler.absence_other_resp)
    # Для «другое» — просто поддержка, без follow-up вопроса


# ── Follow-up «Ну что, сделаем тренировку?» ──────────────────────────────────

async def _delayed_return_question(bot, user_id: int, delay: int = 300) -> None:
    """Через `delay` секунд присылаем вопрос о готовности тренироваться."""
    await asyncio.sleep(delay)
    try:
        await bot.send_message(
            chat_id=user_id,
            text=T.scheduler.absence_return_q,
            reply_markup=kb_return_training(),
        )
    except Exception:
        logger.warning("Could not send return question to user %s", user_id)


@router.callback_query(F.data == "absence:return:yes")
async def absence_return_yes(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Пользователь готов тренироваться — запускаем чекин."""
    from handlers.checkin import _check_yesterday_and_start, _start_checkin
    from services.session_log_service import SessionLogService
    from services.user_service import UserService

    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user or user.status != "active":
        return

    log_svc = SessionLogService(session)
    log = await log_svc.get_today(callback.from_user.id)

    # Если чекин уже пройден сегодня (маловероятно, но возможно)
    if log and log.checkin_done:
        if log.completion_status is not None:
            await callback.message.answer(T.checkin.edit_blocked_completed)
            return
        await _start_checkin(callback, state)
        return

    if await _check_yesterday_and_start(callback, state, log_svc):
        return
    await _start_checkin(callback, state)


@router.callback_query(F.data == "absence:return:no")
async def absence_return_no(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(
        T.scheduler.absence_return_no_text,
        reply_markup=kb_main_menu(),
    )
