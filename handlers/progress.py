from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.utils import safe_answer
from keyboards.builders import kb_main_menu, kb_progress_menu
from services.session_log_service import SessionLogService
from services.user_service import UserService
from services.workout_service import WorkoutService

router = Router()

LEVEL_NAMES = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}

DAY_TYPE_LABELS = {
    "run": "🏃 Бег",
    "strength": "💪 Силовая",
    "recovery": "🔄 Восстановление",
    "rest": "😴 Отдых",
}


async def _send_progress(target, user_id: int, session: AsyncSession) -> None:
    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)

    user = await user_svc.get(user_id)
    if not user or not user.onboarding_complete:
        text = "Сначала нужно пройти онбординг. Напиши /start"
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return

    if user.status != "active":
        text = "⏳ Ожидаем подтверждения тренера. Как только уровень будет подтверждён — программа начнётся!"
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return

    day = await user_svc.current_program_day(user) or 1
    completed = await log_svc.completed_count(user_id)
    streak = await log_svc.streak(user_id)
    level_name = LEVEL_NAMES.get(user.level, "—")

    week_num = (day - 1) // 7 + 1
    week_start, week_end = user_svc.current_week_range(day)
    week_rate = await log_svc.week_completion_rate(user_id, week_start, week_end)
    week_pct = int(week_rate * 100)

    days_into_week = day - week_start + 1
    at_risk = week_rate < 0.75 and days_into_week >= 4

    week_line = f"📆 Неделя {week_num} из 4: <b>{week_pct}% выполнено</b>"
    if at_risk:
        week_line += " ⚠️ <i>(меньше 75% — неделя может повториться)</i>"

    # Week ahead: next 7 days from current day
    ahead_lines = []
    for i in range(7):
        future_day = day + i
        if future_day > 28:
            break
        day_type = await wk_svc.get_day_type(user.level, future_day) or "run"
        label = DAY_TYPE_LABELS.get(day_type, day_type)
        marker = "👉" if i == 0 else "•"
        ahead_lines.append(f"{marker} День {future_day} — {label}")

    week_ahead = "\n".join(ahead_lines) if ahead_lines else ""

    text = (
        f"📊 <b>Твой прогресс</b>\n\n"
        f"🏃 Уровень: <b>{level_name}</b>\n"
        f"📅 День программы: <b>{day} из 28</b>\n"
        f"{week_line}\n"
        f"✅ Тренировок выполнено: <b>{completed}</b>\n"
        f"🔥 Серия активности: <b>{streak} дн.</b>\n\n"
        f"<b>Ближайшие дни:</b>\n{week_ahead}\n\n"
        f"{'🎉 Программа завершена!' if day >= 28 else 'Продолжай в том же духе!'}"
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_reply_markup()
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb_progress_menu())
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb_progress_menu())


@router.message(Command("progress"))
async def cmd_progress(message: Message, session: AsyncSession) -> None:
    await _send_progress(message, message.from_user.id, session)


@router.callback_query(F.data == "menu:progress")
async def cb_progress(callback: CallbackQuery, session: AsyncSession) -> None:
    await _send_progress(callback, callback.from_user.id, session)


@router.callback_query(F.data == "menu:reset_day")
async def cb_reset_day(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Reset today's check-in and workout completion so user can start the day over."""
    log_svc = SessionLogService(session)
    log = await log_svc.get_today(callback.from_user.id)

    if not log:
        await safe_answer(callback, text="Сегодняшний день ещё не начат.", show_alert=True)
        return

    await log_svc.update(
        log,
        checkin_done=False,
        wellbeing=None,
        sleep_quality=None,
        pain_level=None,
        pain_increases=None,
        assigned_workout_id=None,
        assigned_version=None,
        red_flag=False,
        fatigue_reduction=False,
        completion_status=None,
        effort_level=None,
        completion_pain=None,
    )

    await state.clear()
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(
        "🔄 День сброшен. Можешь начать чек-ин заново!\n\n"
        "Нажми «Сегодняшняя тренировка» 👇",
        reply_markup=kb_main_menu(),
    )
