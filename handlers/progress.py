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
from texts import T

router = Router()

LEVEL_NAMES = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}
DAY_TYPE_LABELS = T.progress.day_type_labels


async def _send_progress(target, user_id: int, session: AsyncSession) -> None:
    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)

    user = await user_svc.get(user_id)
    if not user or not user.onboarding_complete:
        text = T.progress.not_onboarded
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return

    if user.status != "active":
        text = T.progress.pending_trainer
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return

    # calendar_day — what user sees ("День X из 28"), never goes back
    # template_day — which workout week template to use (can repeat)
    calendar_day = await user_svc.current_calendar_day(user) or 1
    template_day = await user_svc.current_template_day(user) or 1
    completed = await log_svc.completed_count(user_id)
    streak = await log_svc.streak(user_id)
    level_name = LEVEL_NAMES.get(user.level, "—")

    week_num = (calendar_day - 1) // 7 + 1
    week_start, week_end = user_svc.current_week_range(template_day)
    week_rate = await log_svc.week_completion_rate(user_id, week_start, week_end)
    week_pct = int(week_rate * 100)

    days_into_week = template_day - week_start + 1
    at_risk = week_rate < 0.75 and days_into_week >= 4

    week_line = T.progress.week_line.format(week_num=week_num, week_pct=week_pct)
    if at_risk:
        week_line += T.progress.week_at_risk

    # Week ahead: show calendar days, look up workout type by template day
    ahead_lines = []
    for i in range(7):
        future_cal = calendar_day + i
        future_tmpl = template_day + i
        if future_cal > 28:
            break
        day_type = await wk_svc.get_day_type(user.level, min(future_tmpl, 28)) or "run"
        label = DAY_TYPE_LABELS.get(day_type, day_type)
        marker = "👉" if i == 0 else "•"
        ahead_lines.append(T.progress.ahead_day_fmt.format(marker=marker, cal_day=future_cal, label=label))

    week_ahead = "\n".join(ahead_lines) if ahead_lines else ""
    completion_status = T.progress.program_complete if calendar_day >= 28 else T.progress.keep_going

    text = T.progress.progress_text.format(
        level_name=level_name,
        calendar_day=calendar_day,
        week_line=week_line,
        completed=completed,
        streak=streak,
        week_ahead=week_ahead,
        completion_status=completion_status,
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_reply_markup()
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb_progress_menu())
        await safe_answer(target)
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
        await safe_answer(callback, text=T.progress.day_not_started, show_alert=True)
        return

    await log_svc.update(
        log,
        checkin_done=False,
        wellbeing=None,
        sleep_quality=None,
        pain_level=None,
        pain_increases=None,
        stress_level=None,
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
    await callback.message.answer(T.progress.reset_done, reply_markup=kb_main_menu())
