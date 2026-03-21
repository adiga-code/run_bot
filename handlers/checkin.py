from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from data.interpretations import get_interpretation
from engine.red_flags import CheckinData
from engine.rule_engine import decide_workout_version
from keyboards.builders import (
    kb_main_menu, kb_pain_checkin, kb_pain_increases_checkin,
    kb_sleep, kb_stress, kb_wellbeing,
)
from handlers.utils import safe_answer
from services.session_log_service import SessionLogService
from services.user_service import UserService
from services.workout_service import WorkoutService

router = Router()


class CheckinStates(StatesGroup):
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


@router.message(Command("checkin"))
async def cmd_checkin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_svc = UserService(session)
    user = await user_svc.get(message.from_user.id)
    if not user or not user.onboarding_complete:
        await message.answer("Сначала нужно пройти онбординг. Напиши /start")
        return
    await _start_checkin(message, state)


@router.callback_query(F.data == "menu:today")
async def cb_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user_svc = UserService(session)
    user = await user_svc.get(callback.from_user.id)
    if not user or not user.onboarding_complete:
        await safe_answer(callback, text="Сначала пройди онбординг.", show_alert=True)
        return

    log_svc = SessionLogService(session)
    log = await log_svc.get_today(callback.from_user.id)
    if log and log.checkin_done:
        await safe_answer(callback, text="Ты уже сделал(а) чек-ин сегодня!", show_alert=True)
        return

    await callback.message.edit_reply_markup()
    await _start_checkin(callback, state)
    await safe_answer(callback)


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
async def ci_pain(callback: CallbackQuery, state: FSMContext) -> None:
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
            "🧠 Был ли сильный внешний стресс за последние 24 часа?",
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
        "🧠 Был ли сильный внешний стресс за последние 24 часа?",
        reply_markup=kb_stress(),
    )


# ── Stress ────────────────────────────────────────────────────────────────────

@router.callback_query(CheckinStates.stress, F.data.startswith("ci:stress:"))
async def ci_stress(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    value = int(callback.data.split(":")[2])
    await state.update_data(stress=value)
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
        stress_level=data.get("stress", 1),
    )

    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)

    user = await user_svc.get_or_raise(user_id)
    day_index = await user_svc.current_program_day(user) or 1
    recent_logs = await log_svc.get_recent(user_id)
    day_type = await wk_svc.get_day_type(user.level, day_index) or "run"

    # Get yesterday's day type for after-strength constraint
    prev_day_type = await wk_svc.get_day_type(user.level, max(1, day_index - 1))

    decision = decide_workout_version(checkin, recent_logs, day_type, prev_day_type)
    workout = await wk_svc.get(
        user.level, day_index, decision.version,
        strength_format=user.strength_format if day_type == "strength" else None,
    )

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
    )

    interpretation = get_interpretation(
        version=decision.version,
        checkin_wellbeing=checkin.wellbeing,
        red_flag=decision.red_flag,
        fatigue_reduction=decision.fatigue_reduction,
    )
    await callback.message.answer(interpretation)

    if workout:
        micro = f"\n\n💡 <i>{workout.micro_learning}</i>" if workout.micro_learning else ""
        await callback.message.answer(
            f"📋 <b>День {day_index} из 28 — {workout.title}</b>\n\n"
            f"{workout.text}{micro}",
            parse_mode="HTML",
            reply_markup=kb_main_menu(),
        )
    else:
        await callback.message.answer(
            f"День {day_index} из 28. Тренировка загружается...",
            reply_markup=kb_main_menu(),
        )
