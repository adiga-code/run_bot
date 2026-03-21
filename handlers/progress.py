from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.builders import kb_main_menu
from services.session_log_service import SessionLogService
from services.user_service import UserService

router = Router()

LEVEL_NAMES = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}


async def _send_progress(target, user_id: int, session: AsyncSession) -> None:
    user_svc = UserService(session)
    log_svc = SessionLogService(session)

    user = await user_svc.get(user_id)
    if not user or not user.onboarding_complete:
        text = "Сначала нужно пройти онбординг. Напиши /start"
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return

    day = await user_svc.current_program_day(user) or 1
    completed = await log_svc.completed_count(user_id)
    streak = await log_svc.streak(user_id)
    level_name = LEVEL_NAMES.get(user.level, "—")

    week_num = (day - 1) // 7 + 1  # 1-4
    week_start, week_end = user_svc.current_week_range(day)
    week_rate = await log_svc.week_completion_rate(user_id, week_start, week_end)
    week_pct = int(week_rate * 100)

    # Warn if week is at risk of being repeated (< 75% and more than half the week done)
    days_into_week = day - week_start + 1
    at_risk = week_rate < 0.75 and days_into_week >= 4

    week_line = f"📆 Неделя {week_num} из 4: <b>{week_pct}% выполнено</b>"
    if at_risk:
        week_line += " ⚠️ <i>(меньше 75% — неделя может повториться)</i>"

    text = (
        f"📊 <b>Твой прогресс</b>\n\n"
        f"🏃 Уровень: <b>{level_name}</b>\n"
        f"📅 День программы: <b>{day} из 28</b>\n"
        f"{week_line}\n"
        f"✅ Тренировок выполнено: <b>{completed}</b>\n"
        f"🔥 Серия без пропусков: <b>{streak}</b>\n\n"
        f"{'🎉 Программа завершена!' if day >= 28 else 'Продолжай в том же духе!'}"
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_reply_markup()
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb_main_menu())
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb_main_menu())


@router.message(Command("progress"))
async def cmd_progress(message: Message, session: AsyncSession) -> None:
    await _send_progress(message, message.from_user.id, session)


@router.callback_query(F.data == "menu:progress")
async def cb_progress(callback: CallbackQuery, session: AsyncSession) -> None:
    await _send_progress(callback, callback.from_user.id, session)
