from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.utils import safe_answer
from keyboards.builders import kb_completion, kb_effort, kb_had_pain, kb_main_menu, kb_strength_day_options
from services.session_log_service import SessionLogService

router = Router()

ENCOURAGING_MESSAGES = {
    "done": "🔥 Отлично! Ещё один день программы позади. Ты делаешь это!",
    "partial": "💪 Молодец, что вышел(ла)! Частично — лучше, чем совсем пропустить.",
    "skipped": "😌 Бывает. Главное — не пропускать два дня подряд. Завтра — новый шанс!",
}


class WorkoutStates(StatesGroup):
    completion = State()
    effort = State()
    had_pain = State()


BASIC_WORKOUT_TEXT = (
    "🏃 <b>Базовая тренировка:</b>\n\n"
    "- Приседания — 3×15\n"
    "- Отжимания — 3×10\n"
    "- Выпады — 3×10/нога\n"
    "- Планка — 3×30 сек\n"
    "- Скручивания — 3×15"
)


@router.callback_query(F.data == "wk:mark")
async def cb_mark_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WorkoutStates.completion)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await callback.message.answer(
        "Как прошла тренировка?",
        reply_markup=kb_completion(),
    )


@router.callback_query(F.data == "wk:custom")
async def cb_custom_workout(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(WorkoutStates.completion)
    await callback.message.answer(
        f"{BASIC_WORKOUT_TEXT}\n\nОтметь результат после выполнения:",
        parse_mode="HTML",
        reply_markup=kb_completion(),
    )


@router.callback_query(WorkoutStates.completion, F.data.startswith("wk:status:"))
async def cb_completion_status(callback: CallbackQuery, state: FSMContext) -> None:
    status = callback.data.split(":")[2]
    await state.update_data(status=status)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if status == "skipped":
        await state.clear()
        await _save_completion(callback, {"status": "skipped", "effort": None, "had_pain": None}, None)
        return

    await state.set_state(WorkoutStates.effort)
    await callback.message.answer(
        "Насколько тяжело было?\n(1 — легко, 5 — очень тяжело)",
        reply_markup=kb_effort(),
    )


@router.callback_query(WorkoutStates.effort, F.data.startswith("wk:effort:"))
async def cb_effort(callback: CallbackQuery, state: FSMContext) -> None:
    effort = int(callback.data.split(":")[2])
    await state.update_data(effort=effort)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(WorkoutStates.had_pain)
    await callback.message.answer("Была ли боль во время тренировки?", reply_markup=kb_had_pain())


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
        ENCOURAGING_MESSAGES.get(data["status"], "Записал!"),
        reply_markup=kb_main_menu(),
    )

    # Day 28 — program complete
    if log and log.day_index == 28 and data["status"] in ("done", "partial"):
        await callback.message.answer(
            "🏅 <b>Ты прошёл(ла) 28-дневную программу!</b>\n\n"
            "Это не просто цифра — это 28 дней дисциплины, работы над собой и доверия процессу.\n\n"
            "Ты справился(ась). Так держать! 💪🔥",
            parse_mode="HTML",
        )
