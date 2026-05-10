"""
handlers/checkin.py
Утренний check-in: старая (28-день) и новая (WeekPlan) системы параллельно.
Ключевое условие: user.current_period is not None → новая система.
"""
import logging
from datetime import date, datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from data.interpretations import get_interpretation
from texts import T
from engine.rule_engine import CheckinData, RecentDayData, WorkoutDecision, decide_workout_version
from engine.workout_renderer import (
    RenderedWorkout, render_workout, render_rest_day, render_recovery_day,
    render_run_workout, render_strength_from_template,
)
from keyboards.builders import (
    kb_main_menu, kb_completion, kb_completion_strength, kb_mark_workout,
    kb_pain_checkin, kb_sleep, kb_stress, kb_wellbeing,
    kb_yesterday_completion, kb_checkin_approve, kb_checkin_repeat,
    kb_absence_reason,
)
from handlers.utils import safe_answer, filter_strength_text, get_tip_lines, send_workout_to_user
from services.session_log_service import SessionLogService
from services.user_service import UserService
from services.workout_service import WorkoutService
from services.week_plan_service import WeekPlanService

logger = logging.getLogger(__name__)

_WELLBEING_LABELS = T.checkin.wellbeing_labels
_SLEEP_LABELS     = T.checkin.sleep_labels
_PAIN_LABELS      = T.checkin.pain_labels
_STRESS_LABELS    = T.checkin.stress_labels
_VERSION_LABELS   = T.checkin.version_labels
_PAIN_HIST        = T.checkin.pain_hist
_WELLBEING_HIST   = T.checkin.wellbeing_hist
_DAY_TYPE_LABELS  = T.checkin.day_type_labels


def _build_history_line(recent_logs) -> str:
    """One-line summary of the last N logs for the admin approval card."""
    if not recent_logs:
        return ""
    parts = []
    for log in recent_logs:
        wb = _WELLBEING_HIST.get(log.wellbeing, "?")
        pain = _PAIN_HIST.get(log.pain_level, "?")
        parts.append(T.checkin.history_line_fmt.format(wb=wb, pain=pain))
    return T.checkin.history_header.format(parts=" → ".join(parts))


router = Router()


class CheckinStates(StatesGroup):
    yesterday = State()
    wellbeing = State()
    sleep = State()
    pain = State()
    stress = State()


async def _start_checkin(target, state: FSMContext) -> None:
    await state.set_state(CheckinStates.wellbeing)
    text = T.checkin.morning_question
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, parse_mode="HTML", reply_markup=kb_wellbeing())
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb_wellbeing())


async def _check_yesterday_and_start(
    target, state: FSMContext, log_svc: SessionLogService
) -> bool:
    """Check if yesterday's log needs completion. Returns True if we intercepted."""
    user_id = target.from_user.id
    yesterday_log = await log_svc.get_yesterday(user_id)
    if yesterday_log and yesterday_log.completion_status is None:
        await state.set_state(CheckinStates.yesterday)
        text = T.checkin.yesterday_question
        if isinstance(target, Message):
            await target.answer(text, reply_markup=kb_yesterday_completion())
        else:
            await target.message.answer(text, reply_markup=kb_yesterday_completion())
        return True
    return False


@router.message(Command("checkin"))
async def cmd_checkin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_svc = UserService(session)
    user = await user_svc.get(message.from_user.id)
    if not user or not user.onboarding_complete:
        await message.answer(T.checkin.not_onboarded_cmd)
        return
    if user.status != "active":
        await message.answer(T.checkin.pending_trainer_cmd)
        return

    log_svc = SessionLogService(session)
    log = await log_svc.get_today(message.from_user.id)
    if log and log.checkin_done:
        await message.answer(T.checkin.already_done_today, reply_markup=kb_checkin_repeat())
        return
    if await _check_yesterday_and_start(message, state, log_svc):
        return
    await _start_checkin(message, state)


@router.callback_query(F.data == "ci:recheck:yes")
async def ci_recheck_yes(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    log_svc = SessionLogService(session)
    if await _check_yesterday_and_start(callback, state, log_svc):
        return
    await _start_checkin(callback, state)


@router.callback_query(F.data == "ci:recheck:no")
async def ci_recheck_no(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback, text=T.checkin.recheck_cancelled)


@router.callback_query(F.data == "menu:checkin")
async def cb_menu_checkin(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """
    Кнопка «Утренний check-in» / «Изменить check-in» в главном меню.
    - Чекин не пройден → запускаем чекин.
    - Чекин пройден, тренировка не отмечена → запускаем FSM повторно (изменить).
    - Тренировка уже отмечена → предупреждение.
    """
    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await safe_answer(callback, text=T.checkin.not_onboarded_cb, show_alert=True)
        return
    if user.status != "active":
        await safe_answer(callback, text=T.checkin.pending_trainer_cb, show_alert=True)
        return

    log_svc = SessionLogService(session)
    log = await log_svc.get_today(callback.from_user.id)

    if log and log.checkin_done:
        # Тренировка уже выполнена — нельзя менять чекин
        if log.completion_status is not None:
            await safe_answer(callback, text=T.checkin.edit_blocked_completed, show_alert=True)
            return
        # Тренировка ещё не выполнена — разрешаем изменить чекин
        await callback.message.edit_reply_markup()
        await safe_answer(callback)
        await _start_checkin(callback, state)
        return

    # Чекин ещё не пройден — обычный старт
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    if await _check_yesterday_and_start(callback, state, log_svc):
        return
    await _start_checkin(callback, state)


@router.callback_query(F.data == "menu:today")
async def cb_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await safe_answer(callback, text=T.checkin.not_onboarded_cb, show_alert=True)
        return
    if user.status != "active":
        await safe_answer(callback, text=T.checkin.pending_trainer_cb, show_alert=True)
        return

    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)
    log = await log_svc.get_today(callback.from_user.id)

    if log and log.checkin_done:
        await callback.message.edit_reply_markup()
        await safe_answer(callback)

        # Waiting for trainer approval — don't show workout yet
        if log.approval_pending:
            await callback.message.answer(T.checkin.approval_pending, reply_markup=kb_main_menu(checkin_done=True))
            return

        # ── Новая система: рендер по workout_renderer ─────────────────────────
        if user.current_period is not None and log.week_plan_id:
            await _show_today_new(callback, session, user, log)
            return

        # ── Старая система: рендер по old Workout ────────────────────────────
        if log.assigned_workout_id:
            workout = await wk_svc.get_by_id(log.assigned_workout_id)
            if workout:
                workout_text = filter_strength_text(
                    workout.text,
                    user.strength_format if workout.day_type == "strength" else None,
                )
                is_strength = workout.day_type == "strength" and log.assigned_version != "recovery"
                already_marked = log.completion_status is not None
                calendar_day = user_svc.log_calendar_day(user, log)
                template_day = log.day_index
                tips = get_tip_lines(user.level, template_day)
                tips_block = f"\n\n{tips}" if tips else ""
                await callback.message.answer(
                    T.checkin.workout_header.format(calendar_day=calendar_day, max_day=user_svc._max_day(user), title=workout.title) + tips_block + f"\n\n{workout_text}",
                    parse_mode="HTML",
                    reply_markup=(
                        kb_main_menu() if already_marked
                        else kb_completion_strength() if is_strength
                        else kb_completion()
                    ),
                )
                return
        await callback.message.answer(
            T.checkin.checkin_done_msg,
            reply_markup=kb_mark_workout() if log.completion_status is None else kb_main_menu(),
        )
        return

    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(T.checkin.no_checkin_yet, reply_markup=kb_main_menu())


async def _show_today_new(
    callback: CallbackQuery,
    session: AsyncSession,
    user,
    log,
) -> None:
    """Показывает тренировку пользователю в новой системе (по WorkoutTemplate)."""
    from database.models import WorkoutTemplate, DayPlan
    already_marked = log.completion_status is not None

    if log.day_plan_id:
        dp_result = await session.execute(
            select(DayPlan).where(DayPlan.id == log.day_plan_id)
        )
        day_plan = dp_result.scalar_one_or_none()
    else:
        day_plan = None

    if day_plan is None or log.assigned_version in ("rest", None):
        rendered = render_rest_day()
    elif log.assigned_version == "recovery":
        rendered = render_recovery_day()
    else:
        from database.models import WeekPlan
        wp_result = await session.execute(
            select(WeekPlan).where(WeekPlan.id == log.week_plan_id)
        )
        week_plan = wp_result.scalar_one_or_none()
        level = user.level or 1
        minutes = log.planned_minutes or day_plan.planned_minutes or 0

        if day_plan.day_type == "run":
            rendered = render_run_workout(
                run_subtype=day_plan.run_subtype or "easy",
                target_minutes=minutes,
                version=log.assigned_version,
                level=level,
                period=week_plan.period if week_plan else None,
                long_stage=2 if getattr(user, "l1_long_independent", False) else 1,
            )
        elif day_plan.day_type == "strength":
            template = await _get_workout_template(
                session=session,
                level=level,
                period=week_plan.period if week_plan else None,
                day_type="strength",
                run_subtype=None,
                version=log.assigned_version,
                strength_format=user.strength_format,
            )
            if template:
                rendered = render_strength_from_template(template, minutes, log.assigned_version)
            else:
                rendered = RenderedWorkout(
                    title="Силовая тренировка",
                    text=T.checkin.no_template_fallback,
                    planned_minutes=minutes,
                    version=log.assigned_version or "base",
                )
        else:
            rendered = render_rest_day()

    is_strength = day_plan is not None and day_plan.day_type == "strength" and log.assigned_version != "recovery"
    header = T.checkin.workout_header_new.format(
        week=log.week_plan_id or "—",
        dow=log.day_of_week or "—",
        title=rendered.title,
    )
    await callback.message.answer(
        f"{header}\n\n{rendered.text}",
        parse_mode="HTML",
        reply_markup=(
            kb_main_menu() if already_marked
            else kb_completion_strength() if is_strength
            else kb_completion()
        ),
    )


# ── Yesterday completion ──────────────────────────────────────────────────────

@router.callback_query(CheckinStates.yesterday, F.data.startswith("ci:yday:"))
async def ci_yesterday(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    status = callback.data.split(":")[2]  # done / partial / skipped
    log_svc = SessionLogService(session)
    yesterday_log = await log_svc.get_yesterday(callback.from_user.id)
    if yesterday_log:
        await log_svc.update(yesterday_log, completion_status=status)
        logger.info("User %s marked yesterday as %s", callback.from_user.id, status)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await _start_checkin(callback, state)


# ── Wellbeing ─────────────────────────────────────────────────────────────��───

@router.callback_query(CheckinStates.wellbeing, F.data.startswith("ci:wellbeing:"))
async def ci_wellbeing(callback: CallbackQuery, state: FSMContext) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(wellbeing=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(CheckinStates.sleep)
    await callback.message.answer(T.checkin.sleep_question, reply_markup=kb_sleep())


# ── Sleep ─────────────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.sleep, F.data.startswith("ci:sleep:"))
async def ci_sleep(callback: CallbackQuery, state: FSMContext) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(sleep=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(CheckinStates.pain)
    await callback.message.answer(T.checkin.pain_question, reply_markup=kb_pain_checkin())


# ── Pain info (кнопка «подробнее») ───────────────────────────────────────────

@router.callback_query(F.data == "ci:pain_info")
async def ci_pain_info(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    await callback.message.answer(T.checkin.pain_info)


# ── Pain ──────────────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.pain, F.data.startswith("ci:pain:"))
async def ci_pain(callback: CallbackQuery, state: FSMContext) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(pain=value)
    await callback.message.edit_reply_markup()

    # Для боли ≥ 2 показываем предупреждение
    if value >= 2:
        await callback.answer(T.checkin.pain_warning, show_alert=True)
    else:
        await safe_answer(callback)

    await state.set_state(CheckinStates.stress)
    await callback.message.answer(T.checkin.stress_question, reply_markup=kb_stress())


# ── Stress ────────────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.stress, F.data.startswith("ci:stress:"))
async def ci_stress(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(stress_level=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    data = await state.get_data()
    await state.clear()
    await _finish_checkin(callback, data, session)


# ════════════════════════════════════════════════════════════���═════════════════
# Core logic — dispatcher
# ══════════════════════════════════════════════════════════════════════════════

async def _finish_checkin(
    callback: CallbackQuery,
    data: dict,
    session: AsyncSession,
) -> None:
    checkin = CheckinData(
        wellbeing=data["wellbeing"],
        sleep_quality=data["sleep"],
        pain_level=data["pain"],
        stress_level=data.get("stress_level", 1),
    )

    user_svc = UserService(session)
    user = await user_svc.get_or_raise(callback.from_user.id)

    # ── Маршрутизация: новая система vs старая 28-день ────────────────────────
    if user.current_period is not None:
        await _finish_checkin_new(callback, checkin, session, user)
    else:
        await _finish_checkin_old(callback, checkin, session, user)


# ═════════════════════════════════���════════════════════════════════════════════
# NEW system path (WeekPlan / WorkoutTemplate)
# ══════════════════════════════════════════════════════════════════════════════

async def _finish_checkin_new(
    callback: CallbackQuery,
    checkin: CheckinData,
    session: AsyncSession,
    user,
) -> None:
    user_id = callback.from_user.id
    log_svc = SessionLogService(session)
    wk_plan_svc = WeekPlanService(session)

    # Получаем WeekPlan и DayPlan на сегодня
    week_plan = await wk_plan_svc.get_current(user_id)
    day_plan = None
    if week_plan:
        today_dow = date.today().isoweekday()
        for dp in week_plan.days:
            if dp.day_of_week == today_dow:
                day_plan = dp
                break

    if not week_plan or not day_plan:
        # Нет активного плана — сохраняем чекин без тренировки
        log, _ = await log_svc.get_or_create_today(user_id, date.today().isoweekday())
        await log_svc.update(
            log,
            wellbeing=checkin.wellbeing,
            sleep_quality=checkin.sleep_quality,
            pain_level=checkin.pain_level,
            stress_level=checkin.stress_level,
            checkin_done=True,
            checkin_at=datetime.now(timezone.utc),
        )
        await callback.message.answer(T.checkin.no_plan_yet, reply_markup=kb_main_menu(checkin_done=True))
        return

    # Manual mode (L4/L5): тренер ведёт вручную
    level = user.level or 1
    is_manual = level >= 4
    if is_manual:
        await _finish_checkin_manual(callback, checkin, session, user, week_plan, day_plan)
        return

    # Вчерашний лог для детектора "возврат после боли"
    yesterday_log = await log_svc.get_yesterday(user_id)
    yesterday_data = RecentDayData(
        pain_level=yesterday_log.pain_level if yesterday_log and yesterday_log.pain_level else 1
    )

    # Решение о версии тренировки
    decision = decide_workout_version(checkin, day_plan.day_type, yesterday_data)

    # Рендер тренировки
    minutes = day_plan.planned_minutes or 0
    if decision.version == "rest" or day_plan.day_type == "rest":
        rendered = render_rest_day()
    elif decision.version == "recovery":
        rendered = render_recovery_day()
    elif day_plan.day_type == "run":
        rendered = render_run_workout(
            run_subtype=day_plan.run_subtype or "easy",
            target_minutes=minutes,
            version=decision.version,
            level=level,
            period=week_plan.period,
            long_stage=2 if getattr(user, "l1_long_independent", False) else 1,
        )
    elif day_plan.day_type == "strength":
        template = await _get_workout_template(
            session=session,
            level=level,
            period=week_plan.period,
            day_type="strength",
            run_subtype=None,
            version=decision.version,
            strength_format=user.strength_format,
        )
        if template:
            rendered = render_strength_from_template(template, minutes, decision.version)
        else:
            rendered = RenderedWorkout(
                title="Силовая тренировка",
                text=T.checkin.no_template_fallback,
                planned_minutes=minutes,
                version=decision.version,
            )
    else:
        rendered = render_rest_day()

    now = datetime.now(timezone.utc)
    user_is_admin = user_id in settings.admin_ids

    log, created = await log_svc.get_or_create_today(user_id, day_plan.day_of_week)
    is_recheck = not created
    recheckin_count = (getattr(log, "recheckin_count", 0) or 0) + (1 if is_recheck else 0)

    await log_svc.update(
        log,
        wellbeing=checkin.wellbeing,
        sleep_quality=checkin.sleep_quality,
        pain_level=checkin.pain_level,
        stress_level=checkin.stress_level,
        assigned_version=decision.version,
        checkin_done=True,
        approval_pending=not user_is_admin,
        checkin_at=now,
        # Поля новой системы
        week_plan_id=week_plan.id,
        day_plan_id=day_plan.id,
        day_of_week=day_plan.day_of_week,
        planned_minutes=rendered.planned_minutes,
        recheckin_count=recheckin_count,
        last_checkin_at=now,
    )

    logger.info(
        "Checkin (new) user=%s dow=%s period=%s version=%s reason=%s",
        user_id, day_plan.day_of_week, week_plan.period, decision.version, decision.reason,
    )

    # Отправляем интерпретацию пользователю
    try:
        interpretation = get_interpretation(
            version=decision.version,
            checkin_wellbeing=checkin.wellbeing,
            red_flag=False,
            fatigue_reduction=False,
            pain_level=checkin.pain_level,
        )
        await callback.message.answer(interpretation)
    except Exception:
        pass

    if user_is_admin:
        # Тренер сам проверяет — отправляем тренировку сразу
        header = T.checkin.workout_header_new.format(
            week=week_plan.week_number,
            dow=day_plan.day_of_week,
            title=rendered.title,
        )
        is_strength = day_plan.day_type == "strength" and decision.version != "recovery"
        await callback.message.answer(
            f"{header}\n\n{rendered.text}",
            parse_mode="HTML",
            reply_markup=kb_completion_strength() if is_strength else kb_completion(),
        )
        return

    # Ждём одобрения тренера
    await callback.message.answer(T.checkin.waiting_trainer, reply_markup=kb_main_menu(checkin_done=True))

    # Карточка для тренера
    day_type_label = _DAY_TYPE_LABELS.get(day_plan.day_type, day_plan.day_type)
    recheck_suffix = T.checkin.recheck_label if is_recheck else ""
    card = T.checkin.admin_card_new.format(
        name=user.full_name + recheck_suffix,
        week=week_plan.week_number,
        period=week_plan.period,
        dow=day_plan.day_of_week,
        day_type=day_type_label,
        wellbeing=_WELLBEING_LABELS.get(checkin.wellbeing, "?"),
        sleep=_SLEEP_LABELS.get(checkin.sleep_quality, "?"),
        pain=_PAIN_LABELS.get(checkin.pain_level, "?"),
        stress=_STRESS_LABELS.get(checkin.stress_level, "?"),
        version=_VERSION_LABELS.get(decision.version, decision.version),
        reason=decision.reason,
        minutes=rendered.planned_minutes,
    )
    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=card,
                parse_mode="HTML",
                reply_markup=kb_checkin_approve(user_id),
            )
        except Exception:
            logger.warning("Could not send approval card to admin %s", admin_id)


async def _finish_checkin_manual(
    callback: CallbackQuery,
    checkin: CheckinData,
    session: AsyncSession,
    user,
    week_plan,
    day_plan,
) -> None:
    """L4/L5: сохраняем чекин, отправляем карточку тренеру без авто-версии."""
    user_id = callback.from_user.id
    log_svc = SessionLogService(session)
    now = datetime.now(timezone.utc)
    user_is_admin = user_id in settings.admin_ids

    log, created = await log_svc.get_or_create_today(user_id, day_plan.day_of_week)
    is_recheck = not created

    await log_svc.update(
        log,
        wellbeing=checkin.wellbeing,
        sleep_quality=checkin.sleep_quality,
        pain_level=checkin.pain_level,
        stress_level=checkin.stress_level,
        checkin_done=True,
        approval_pending=not user_is_admin,
        checkin_at=now,
        week_plan_id=week_plan.id,
        day_plan_id=day_plan.id,
        day_of_week=day_plan.day_of_week,
        recheckin_count=(getattr(log, "recheckin_count", 0) or 0) + (1 if is_recheck else 0),
        last_checkin_at=now,
    )

    await callback.message.answer(T.checkin.waiting_trainer, reply_markup=kb_main_menu(checkin_done=True))

    if not user_is_admin:
        card = T.checkin.admin_card_manual.format(
            name=user.full_name,
            wellbeing=_WELLBEING_LABELS.get(checkin.wellbeing, "?"),
            sleep=_SLEEP_LABELS.get(checkin.sleep_quality, "?"),
            pain=_PAIN_LABELS.get(checkin.pain_level, "?"),
            stress=_STRESS_LABELS.get(checkin.stress_level, "?"),
        )
        for admin_id in settings.admin_ids:
            try:
                await callback.bot.send_message(
                    chat_id=admin_id,
                    text=card,
                    parse_mode="HTML",
                    reply_markup=kb_checkin_approve(user_id),
                )
            except Exception:
                logger.warning("Could not send manual card to admin %s", admin_id)


# ═════════════════════════��════════════════════════════════════════════════════
# OLD system path (28-day, Workout table)
# ══════════════════════════════════════════════════════════════════════════════

async def _finish_checkin_old(
    callback: CallbackQuery,
    checkin: CheckinData,
    session: AsyncSession,
    user,
) -> None:
    user_id = callback.from_user.id
    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)
    user_svc = UserService(session)

    calendar_day = await user_svc.current_calendar_day(user) or 1
    template_day = await user_svc.current_template_day(user) or 1
    day_type = await wk_svc.get_day_type(user.level, template_day) or "run"

    # Вчерашний лог для "возврат после боли"
    yesterday_log = await log_svc.get_yesterday(user_id)
    yesterday_data = RecentDayData(
        pain_level=yesterday_log.pain_level if yesterday_log and yesterday_log.pain_level else 1
    )

    decision = decide_workout_version(checkin, day_type, yesterday_data)
    workout = await wk_svc.get(
        user.level, template_day, decision.version,
        strength_format=user.strength_format if day_type == "strength" else None,
    )

    now = datetime.now(timezone.utc)
    user_is_admin = user_id in settings.admin_ids

    log, created = await log_svc.get_or_create_today(user_id, template_day)
    is_recheck = not created
    await log_svc.update(
        log,
        wellbeing=checkin.wellbeing,
        sleep_quality=checkin.sleep_quality,
        pain_level=checkin.pain_level,
        stress_level=checkin.stress_level,
        assigned_workout_id=workout.id if workout else None,
        assigned_version=decision.version,
        checkin_done=True,
        approval_pending=not user_is_admin,
        checkin_at=now,
    )

    logger.info(
        "Checkin (old) user=%s calendar_day=%s template_day=%s "
        "wellbeing=%s sleep=%s pain=%s stress=%s → version=%s",
        user_id, calendar_day, template_day, checkin.wellbeing, checkin.sleep_quality,
        checkin.pain_level, checkin.stress_level, decision.version,
    )

    # Интерпретация
    try:
        interpretation = get_interpretation(
            version=decision.version,
            checkin_wellbeing=checkin.wellbeing,
            red_flag=False,
            fatigue_reduction=False,
            pain_level=checkin.pain_level,
        )
        await callback.message.answer(interpretation)
    except Exception:
        pass

    if user_is_admin:
        if decision.version == "rest" or workout is None:
            await callback.message.answer(T.checkin.rest_day, reply_markup=kb_main_menu(checkin_done=True))
        else:
            await send_workout_to_user(
                callback.bot, user_id, template_day,
                workout, day_type, decision.version, user.strength_format, user.level,
                calendar_day=calendar_day,
                max_day=user_svc._max_day(user),
            )
        return

    await callback.message.answer(T.checkin.waiting_trainer, reply_markup=kb_main_menu(checkin_done=True))

    # Карточка для тренера (старый формат)
    day_type_label = _DAY_TYPE_LABELS.get(day_type, day_type)
    recheck_suffix = T.checkin.recheck_label if is_recheck else ""
    # Получаем последние логи для истории (упрощённо — не используем fatigue)
    card = T.checkin.admin_card.format(
        name=user.full_name + recheck_suffix,
        calendar_day=calendar_day,
        max_day=user_svc._max_day(user),
        day_type=day_type_label,
        wellbeing=_WELLBEING_LABELS.get(checkin.wellbeing, "?"),
        sleep=_SLEEP_LABELS.get(checkin.sleep_quality, "?"),
        pain=_PAIN_LABELS.get(checkin.pain_level, "?"),
        stress=_STRESS_LABELS.get(checkin.stress_level, "?"),
        version=_VERSION_LABELS.get(decision.version, decision.version),
        reason=decision.reason,
    )
    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=card,
                parse_mode="HTML",
                reply_markup=kb_checkin_approve(user_id),
            )
        except Exception:
            logger.warning("Could not send approval card to admin %s", admin_id)


# ══════════════════════════════════════════════════════════════════════════════
# Template lookup helper
# ════════════════════════════════════════════════��═════════════════════════════

async def _get_workout_template(
    session: AsyncSession,
    level: int,
    period: str | None,
    day_type: str,
    run_subtype: str | None,
    version: str,
    strength_format: str | None = None,
):
    """
    Ищет WorkoutTemplate для данных параметров.
    Приоритет: period-специфичный → универсальный (period=NULL).
    """
    from database.models import WorkoutTemplate

    base_filters = [
        WorkoutTemplate.level == level,
        WorkoutTemplate.day_type == day_type,
        WorkoutTemplate.version == version,
    ]
    if run_subtype:
        base_filters.append(WorkoutTemplate.run_subtype == run_subtype)
    if strength_format and day_type == "strength":
        base_filters.append(WorkoutTemplate.strength_format == strength_format)

    # Попытка 1: period-specific
    if period:
        result = await session.execute(
            select(WorkoutTemplate)
            .where(*base_filters, WorkoutTemplate.period == period)
            .limit(1)
        )
        template = result.scalar_one_or_none()
        if template:
            return template

    # Попытка 2: универсальный (period = NULL)
    result = await session.execute(
        select(WorkoutTemplate)
        .where(*base_filters, WorkoutTemplate.period.is_(None))
        .limit(1)
    )
    return result.scalar_one_or_none()
