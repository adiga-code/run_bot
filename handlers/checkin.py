import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from data.interpretations import get_interpretation
from engine.red_flags import CheckinData
from engine.rule_engine import decide_workout_version
from keyboards.builders import (
    kb_main_menu, kb_completion, kb_completion_strength, kb_mark_workout,
    kb_pain_checkin, kb_pain_increases_checkin, kb_sleep, kb_stress, kb_wellbeing,
    kb_yesterday_completion, kb_checkin_approve,
)
from handlers.utils import safe_answer, filter_strength_text, get_tip_lines, send_workout_to_user
from services.session_log_service import SessionLogService
from services.user_service import UserService
from services.workout_service import WorkoutService

logger = logging.getLogger(__name__)

_WELLBEING_LABELS = {1: "плохо", 2: "тяжеловато", 3: "нормально", 4: "хорошо", 5: "отлично"}
_SLEEP_LABELS    = {1: "плохо", 2: "нормально", 3: "хорошо"}
_PAIN_LABELS     = {1: "нет", 2: "немного", 3: "есть"}
_STRESS_LABELS   = {1: "нет", 2: "умеренный", 3: "сильный"}
_VERSION_LABELS  = {"base": "Base (полная)", "light": "Light (лёгкая)", "recovery": "Recovery", "rest": "Отдых"}
_DAY_TYPE_LABELS = {"run": "Бег", "strength": "Силовая", "recovery": "Восстановление", "rest": "Отдых"}

router = Router()


class CheckinStates(StatesGroup):
    yesterday = State()
    wellbeing = State()
    sleep = State()
    pain = State()
    pain_increases = State()
    stress = State()


async def _start_checkin(target, state: FSMContext) -> None:
    await state.set_state(CheckinStates.wellbeing)
    text = "🌅 <b>Утренний чек-ин</b>\n\nКак твоё самочувствие прямо сейчас?"
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
        text = "📅 Вчера у тебя была тренировка — ты её выполнил(а)?"
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
        await message.answer("Сначала нужно пройти онбординг. Напиши /start")
        return
    if user.status != "active":
        await message.answer("⏳ Ожидаем подтверждения тренера.")
        return

    log_svc = SessionLogService(session)
    if await _check_yesterday_and_start(message, state, log_svc):
        return
    await _start_checkin(message, state)


@router.callback_query(F.data == "menu:today")
async def cb_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await safe_answer(callback, text="Сначала пройди онбординг.", show_alert=True)
        return
    if user.status != "active":
        await safe_answer(
            callback,
            text="⏳ Ожидаем подтверждения тренера. Как только уровень будет подтверждён — программа начнётся!",
            show_alert=True,
        )
        return

    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)
    log = await log_svc.get_today(callback.from_user.id)

    if log and log.checkin_done:
        await callback.message.edit_reply_markup()
        await safe_answer(callback)
        if log.assigned_workout_id:
            workout = await wk_svc.get_by_id(log.assigned_workout_id)
            if workout:
                workout_text = filter_strength_text(
                    workout.text,
                    user.strength_format if workout.day_type == "strength" else None,
                )
                is_strength = workout.day_type == "strength" and log.assigned_version != "recovery"
                already_marked = log.completion_status is not None
                tips = get_tip_lines(user.level, log.day_index)
                tips_block = f"\n\n{tips}" if tips else ""
                await callback.message.answer(
                    f"📋 <b>День {log.day_index} из 28 — {workout.title}</b>{tips_block}\n\n{workout_text}",
                    parse_mode="HTML",
                    reply_markup=(
                        kb_main_menu() if already_marked
                        else kb_completion_strength() if is_strength
                        else kb_completion()
                    ),
                )
                return
        await callback.message.answer(
            "Чек-ин уже сделан. Вечером отметь как прошла тренировка!",
            reply_markup=kb_mark_workout() if log.completion_status is None else kb_main_menu(),
        )
        return

    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    if await _check_yesterday_and_start(callback, state, log_svc):
        return
    await _start_checkin(callback, state)


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
    await callback.message.answer("😴 Как ты спал(а) этой ночью?", reply_markup=kb_sleep())


# ── Sleep ─────────────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.sleep, F.data.startswith("ci:sleep:"))
async def ci_sleep(callback: CallbackQuery, state: FSMContext) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(sleep=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(CheckinStates.pain)
    await callback.message.answer(
        "⚡ Есть ли боль или дискомфорт в мышцах / суставах?",
        reply_markup=kb_pain_checkin(),
    )


# ── Pain ──────────────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.pain, F.data.startswith("ci:pain:"))
async def ci_pain(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(pain=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if value > 1:
        await state.set_state(CheckinStates.pain_increases)
        await callback.message.answer(
            "Усиливается ли боль при нагрузке?",
            reply_markup=kb_pain_increases_checkin(),
        )
    else:
        await state.update_data(pain_increases=None)
        await state.set_state(CheckinStates.stress)
        await callback.message.answer(
            "😤 Был ли сильный внешний стресс за последние 24 часа?",
            reply_markup=kb_stress(),
        )


# ── Pain increases ────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.pain_increases, F.data.startswith("ci:pain_inc:"))
async def ci_pain_increases(callback: CallbackQuery, state: FSMContext) -> None:
    raw = callback.data.split(":")[2]
    pain_increases = True if raw == "yes" else (False if raw == "no" else None)
    await state.update_data(pain_increases=pain_increases)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(CheckinStates.stress)
    await callback.message.answer(
        "😤 Был ли сильный внешний стресс за последние 24 часа?",
        reply_markup=kb_stress(),
    )


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
        pain_increases=data.get("pain_increases"),
        stress_level=data.get("stress_level", 1),
    )

    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)

    user = await user_svc.get_or_raise(user_id)
    day_index = await user_svc.current_program_day(user) or 1
    recent_logs = await log_svc.get_recent(user_id)
    day_type = await wk_svc.get_day_type(user.level, day_index) or "run"

    prev_day_type = await wk_svc.get_day_type(user.level, max(1, day_index - 1))

    decision = decide_workout_version(checkin, recent_logs, day_type, prev_day_type)
    workout = await wk_svc.get(
        user.level, day_index, decision.version,
        strength_format=user.strength_format if day_type == "strength" else None,
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    log, _ = await log_svc.get_or_create_today(user_id, day_index)
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
        approval_pending=True,
        checkin_at=now,
    )

    logger.info(
        "Checkin user=%s wellbeing=%s sleep=%s pain=%s stress=%s → version=%s (pending approval)",
        user_id, checkin.wellbeing, checkin.sleep_quality, checkin.pain_level,
        checkin.stress_level, decision.version,
    )

    # Send interpretation to user, then tell them to wait
    interpretation = get_interpretation(
        version=decision.version,
        checkin_wellbeing=checkin.wellbeing,
        red_flag=decision.red_flag,
        fatigue_reduction=decision.fatigue_reduction,
    )
    await callback.message.answer(interpretation)
    await callback.message.answer(
        "⏳ Тренер проверит твои данные и пришлёт тренировку в ближайшее время.",
        reply_markup=kb_main_menu(),
    )

    # Build approval card for admins
    day_type_label = _DAY_TYPE_LABELS.get(day_type, day_type)
    card = (
        f"👤 <b>{user.full_name}</b> — День {day_index} из 28 ({day_type_label})\n"
        f"Самочувствие: {_WELLBEING_LABELS.get(checkin.wellbeing, '?')} | "
        f"Сон: {_SLEEP_LABELS.get(checkin.sleep_quality, '?')} | "
        f"Боль: {_PAIN_LABELS.get(checkin.pain_level, '?')} | "
        f"Стресс: {_STRESS_LABELS.get(checkin.stress_level, '?')}\n\n"
        f"🤖 Рекомендация: <b>{_VERSION_LABELS.get(decision.version, decision.version)}</b>\n"
        f"📝 {decision.reason}"
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
