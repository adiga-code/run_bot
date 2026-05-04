import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from data.interpretations import get_interpretation
from texts import T
from engine.red_flags import CheckinData
from engine.rule_engine import decide_workout_version
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

logger = logging.getLogger(__name__)

_WELLBEING_LABELS = T.checkin.wellbeing_labels
_SLEEP_LABELS     = T.checkin.sleep_labels
_PAIN_LABELS      = T.checkin.pain_labels
_STRESS_LABELS    = T.checkin.stress_labels
_VERSION_LABELS   = T.checkin.version_labels
_PAIN_HIST        = T.checkin.pain_hist
_WELLBEING_HIST   = T.checkin.wellbeing_hist


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
_DAY_TYPE_LABELS = T.checkin.day_type_labels

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
    user_id = (
        target.from_user.id if isinstance(target, Message) else target.from_user.id
    )
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
                tips = get_tip_lines(user.level, log.day_index)  # template day for tips
                tips_block = f"\n\n{tips}" if tips else ""
                await callback.message.answer(
                    T.checkin.workout_header.format(calendar_day=calendar_day, title=workout.title) + tips_block + f"\n\n{workout_text}",
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


# ── Yesterday completion ──────────────────────────────────────────────────────

@router.callback_query(CheckinStates.yesterday, F.data.startswith("ci:yday:"))
async def ci_yesterday(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    status = callback.data.split(":")[2]  # done / partial / skipped
    log_svc = SessionLogService(session)
    yesterday_log = await log_svc.get_yesterday(callback.from_user.id)
    if yesterday_log:
        await log_svc.update(yesterday_log, completion_status=status)
        logger.info("User %s marked yesterday (day %s) as %s", callback.from_user.id, yesterday_log.day_index, status)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await _start_checkin(callback, state)


# ── Wellbeing ─────────────────────────────────────────────────────────────────

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

    # Для боли ≥ 2 показываем предупреждение об усилении боли в тренировке
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


# ── Core logic ────────────────────────────────────────────────────────────────

async def _finish_checkin(
    callback: CallbackQuery,
    data: dict,
    session: AsyncSession,
) -> None:
    user_id = callback.from_user.id

    checkin = CheckinData(
        wellbeing=data["wellbeing"],
        sleep_quality=data["sleep"],
        pain_level=data["pain"],
        stress_level=data.get("stress_level", 1),
    )

    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)

    user = await user_svc.get_or_raise(user_id)
    calendar_day = await user_svc.current_calendar_day(user) or 1
    template_day = await user_svc.current_template_day(user) or 1
    recent_logs = await log_svc.get_recent(user_id)
    day_type = await wk_svc.get_day_type(user.level, template_day) or "run"

    prev_day_type = await wk_svc.get_day_type(user.level, max(1, template_day - 1))

    decision = decide_workout_version(checkin, recent_logs, day_type, prev_day_type)
    workout = await wk_svc.get(
        user.level, template_day, decision.version,
        strength_format=user.strength_format if day_type == "strength" else None,
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Admins doing their own check-in bypass the approval flow — no trainer needed.
    user_is_admin = user_id in settings.admin_ids

    # Log stores template_day for workout lookups; calendar_day is derived from log.date.
    log, created = await log_svc.get_or_create_today(user_id, template_day)
    is_recheck = not created  # пользователь повторно проходит чекин сегодня
    await log_svc.update(
        log,
        wellbeing=checkin.wellbeing,
        sleep_quality=checkin.sleep_quality,
        pain_level=checkin.pain_level,
        pain_increases=checkin.pain_increases,
        stress_level=checkin.stress_level,
        assigned_workout_id=workout.id if workout else None,
        assigned_version=decision.version,
        red_flag=decision.red_flag,
        fatigue_reduction=decision.fatigue_reduction,
        checkin_done=True,
        approval_pending=not user_is_admin,
        checkin_at=now,
    )

    logger.info(
        "Checkin user=%s calendar_day=%s template_day=%s wellbeing=%s sleep=%s pain=%s stress=%s → version=%s (%s)",
        user_id, calendar_day, template_day, checkin.wellbeing, checkin.sleep_quality,
        checkin.pain_level, checkin.stress_level, decision.version,
        "admin-direct" if user_is_admin else "pending approval",
    )

    # Send interpretation to user
    interpretation = get_interpretation(
        version=decision.version,
        checkin_wellbeing=checkin.wellbeing,
        red_flag=decision.red_flag,
        fatigue_reduction=decision.fatigue_reduction,
        pain_level=checkin.pain_level,
    )
    await callback.message.answer(interpretation)

    if user_is_admin:
        # Send workout directly — no approval card needed
        if decision.version == "rest" or workout is None:
            await callback.message.answer(T.checkin.rest_day, reply_markup=kb_main_menu(checkin_done=True))
        else:
            await send_workout_to_user(
                callback.bot, user_id, template_day,
                workout, day_type, decision.version, user.strength_format, user.level,
                calendar_day=calendar_day,
            )
        return

    await callback.message.answer(T.checkin.waiting_trainer, reply_markup=kb_main_menu(checkin_done=True))

    # Build approval card for non-admin athletes
    day_type_label = _DAY_TYPE_LABELS.get(day_type, day_type)
    history_line = _build_history_line(recent_logs) if decision.fatigue_reduction else ""
    recheck_suffix = T.checkin.recheck_label if is_recheck else ""
    card = T.checkin.admin_card.format(
        name=user.full_name + recheck_suffix,
        calendar_day=calendar_day,
        day_type=day_type_label,
        wellbeing=_WELLBEING_LABELS.get(checkin.wellbeing, "?"),
        sleep=_SLEEP_LABELS.get(checkin.sleep_quality, "?"),
        pain=_PAIN_LABELS.get(checkin.pain_level, "?"),
        stress=_STRESS_LABELS.get(checkin.stress_level, "?"),
        version=_VERSION_LABELS.get(decision.version, decision.version),
        reason=decision.reason,
    ) + (f"\n{history_line}" if history_line else "")
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
