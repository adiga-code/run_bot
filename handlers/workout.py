from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.utils import safe_answer
from keyboards.builders import kb_completion, kb_effort, kb_had_pain, kb_main_menu, kb_completion_strength
from services.session_log_service import SessionLogService
from texts import T

router = Router()

ENCOURAGING_MESSAGES = {
    "done":    T.workout.encouraging_done,
    "partial": T.workout.encouraging_partial,
    "skipped": T.workout.encouraging_skipped,
}


class WorkoutStates(StatesGroup):
    completion = State()
    effort = State()
    had_pain = State()


BASIC_WORKOUT_TEXT = T.workout.basic_workout


@router.callback_query(F.data == "wk:mark")
async def cb_mark_workout(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Evening 'mark workout' button — show completion status picker."""
    log_svc = SessionLogService(session)
    log = await log_svc.get_today(callback.from_user.id)

    if not log:
        await safe_answer(callback, text=T.workout.not_found, show_alert=True)
        return

    if log.completion_status:
        await safe_answer(callback, text=T.workout.already_marked, show_alert=True)
        return

    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(WorkoutStates.completion)

    is_strength = (
        log.assigned_version not in (None, "recovery")
        and log.assigned_workout_id is not None
    )
    await callback.message.answer(
        T.workout.ask_completion,
        reply_markup=kb_completion_strength() if is_strength else kb_completion(),
    )


@router.callback_query(F.data == "wk:custom")
async def cb_custom_workout(callback: CallbackQuery, state: FSMContext) -> None:
    """Replace the workout message with basic workout + completion buttons."""
    await safe_answer(callback)
    await state.set_state(WorkoutStates.completion)
    try:
        await callback.message.edit_text(
            BASIC_WORKOUT_TEXT + T.workout.mark_suffix,
            parse_mode="HTML",
            reply_markup=kb_completion(),
        )
    except Exception:
        await callback.message.answer(
            BASIC_WORKOUT_TEXT + T.workout.mark_suffix,
            parse_mode="HTML",
            reply_markup=kb_completion(),
        )


@router.callback_query(F.data.startswith("wk:status:"))
async def cb_completion_status(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    status = callback.data.split(":")[2]
    await state.set_state(WorkoutStates.completion)
    await state.update_data(status=status)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if status == "skipped":
        await state.clear()
        await _save_completion(callback, {"status": "skipped", "effort": None, "had_pain": None}, session)
        return

    await state.set_state(WorkoutStates.effort)
    await callback.message.answer(T.workout.ask_effort, reply_markup=kb_effort())


@router.callback_query(WorkoutStates.effort, F.data.startswith("wk:effort:"))
async def cb_effort(callback: CallbackQuery, state: FSMContext) -> None:
    effort = int(callback.data.split(":")[2])
    await state.update_data(effort=effort)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(WorkoutStates.had_pain)
    await callback.message.answer(T.workout.ask_pain, reply_markup=kb_had_pain())


@router.callback_query(WorkoutStates.had_pain, F.data.startswith("wk:pain:"))
async def cb_had_pain(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    had_pain = callback.data.split(":")[2] == "yes"
    data = await state.get_data()
    data["had_pain"] = had_pain
    await state.clear()
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await _save_completion(callback, data, session)


async def _save_completion(callback: CallbackQuery, data: dict, session: AsyncSession | None) -> None:
    if session is None:
        await callback.message.answer(
            ENCOURAGING_MESSAGES.get(data["status"], "Записал!"),
            reply_markup=kb_main_menu(),
        )
        return

    log_svc = SessionLogService(session)
    log = await log_svc.get_today(callback.from_user.id)
    if log:
        await log_svc.update(
            log,
            completion_status=data["status"],
            effort_level=data.get("effort"),
            completion_pain=data.get("had_pain"),
            evening_sent=True,
        )

    await callback.message.answer(
        ENCOURAGING_MESSAGES.get(data["status"], T.workout.encouraging_default),
        reply_markup=kb_main_menu(),
    )

    # Day 28 — program complete
    if log and log.day_index == 28 and data["status"] in ("done", "partial"):
        await callback.message.answer(T.workout.program_complete, parse_mode="HTML")
