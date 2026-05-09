from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func
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
DOW_LABELS = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}


# ═════════════════════════════════════════════════════════════════════════════
# Новая цикловая система
# ═════════════════════════════════════════════════════════════════════════════

async def _send_progress_new(target, user_id: int, session: AsyncSession) -> None:
    """Экран прогресса для пользователей новой цикловой системы."""
    from database.models import DayPlan, SessionLog, WeekPlan
    from services.week_plan_service import WeekPlanService

    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    wk_plan_svc = WeekPlanService(session)

    user = await user_svc.get(user_id)
    week_plan = await wk_plan_svc.get_current(user_id)
    streak = await log_svc.streak(user_id)

    level_name = LEVEL_NAMES.get(user.level, "—")
    period_label = T.progress.period_labels.get(
        user.current_period or "", user.current_period or "—"
    )
    week_num = user.program_week_number or 1
    target_min = (
        (week_plan.weekly_target_minutes if week_plan else None)
        or user.weekly_target_minutes
        or 0
    )

    # ── Статистика текущей недели ────────────────────────────────────────────
    done, total = 0, 0
    if week_plan:
        total_res = await session.execute(
            select(func.count()).where(
                DayPlan.week_plan_id == week_plan.id,
                DayPlan.day_type != "rest",
            )
        )
        total = total_res.scalar_one()

        done_res = await session.execute(
            select(func.count()).where(
                SessionLog.week_plan_id == week_plan.id,
                SessionLog.completion_status == "done",
            )
        )
        done = done_res.scalar_one()

    week_pct = int(done / total * 100) if total > 0 else 0

    # ── Ближайшие дни текущей недели (сегодня и далее) ──────────────────────
    ahead_lines = []
    if week_plan and week_plan.days:
        today_dow = date.today().isoweekday()
        for dp in sorted(week_plan.days, key=lambda d: d.day_of_week):
            if dp.day_of_week < today_dow:
                continue
            marker = "👉" if dp.day_of_week == today_dow else "•"
            type_label = DAY_TYPE_LABELS.get(dp.day_type, dp.day_type)
            subtype = ""
            if dp.run_subtype:
                sub_label = T.progress.run_subtype_labels.get(dp.run_subtype, "")
                subtype = f" ({sub_label})" if sub_label else ""
            mins = f" · {dp.planned_minutes} мин" if dp.planned_minutes else ""
            dow = DOW_LABELS.get(dp.day_of_week, str(dp.day_of_week))
            ahead_lines.append(f"{marker} {dow} — {type_label}{subtype}{mins}")

    if ahead_lines:
        week_ahead = "<b>Ближайшие дни:</b>\n" + "\n".join(ahead_lines) + "\n\n"
    elif week_plan:
        week_ahead = "<i>Неделя завершена.</i>\n\n"
    else:
        week_ahead = T.progress.no_week_plan

    # ── Доп. флаги ───────────────────────────────────────────────────────────
    extra_parts = []
    if week_plan and week_plan.is_recovery_week:
        extra_parts.append(T.progress.recovery_week_notice)
    if week_plan and week_plan.is_rollback_week:
        extra_parts.append(T.progress.rollback_notice)
    if getattr(user, "red_flag_active", False):
        extra_parts.append(T.progress.red_flag_warning)
    extra = "\n".join(extra_parts)

    text = T.progress.progress_text_new.format(
        level_name=level_name,
        week_num=week_num,
        period_label=period_label,
        target_min=target_min,
        done=done,
        total=total,
        week_pct=week_pct,
        streak=streak,
        week_ahead=week_ahead,
        extra=extra,
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_reply_markup()
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb_progress_menu())
        await safe_answer(target)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb_progress_menu())


# ═════════════════════════════════════════════════════════════════════════════
# Старая 28-дневная система
# ═════════════════════════════════════════════════════════════════════════════

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

    # ── Маршрутизация: новая система vs старая 28-день ────────────────────────
    if user.current_period is not None:
        await _send_progress_new(target, user_id, session)
        return

    # calendar_day — what user sees ("День X из N"), never goes back
    # template_day — which workout week template to use (can repeat)
    calendar_day = await user_svc.current_calendar_day(user) or 1
    template_day = await user_svc.current_template_day(user) or 1
    max_day = user_svc._max_day(user)
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
        if future_cal > max_day:
            break
        day_type = await wk_svc.get_day_type(user.level, min(future_tmpl, max_day)) or "run"
        label = DAY_TYPE_LABELS.get(day_type, day_type)
        marker = "👉" if i == 0 else "•"
        ahead_lines.append(T.progress.ahead_day_fmt.format(
            marker=marker, cal_day=future_cal, label=label
        ))

    week_ahead = "\n".join(ahead_lines) if ahead_lines else ""
    completion_status = T.progress.program_complete if calendar_day >= max_day else T.progress.keep_going

    text = T.progress.progress_text.format(
        level_name=level_name,
        calendar_day=calendar_day,
        max_day=max_day,
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


# ═════════════════════════════════════════════════════════════════════════════
# Роутеры
# ═════════════════════════════════════════════════════════════════════════════

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
