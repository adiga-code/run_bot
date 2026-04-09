from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from engine.level_assignment import OnboardingAnswers, assign_level
from keyboards.builders import (
    kb_admin_approve, kb_break, kb_experience, kb_frequency, kb_gender,
    kb_goal, kb_injury_history, kb_location, kb_longest_run, kb_main_menu,
    kb_other_sports, kb_pain, kb_pain_increases, kb_pain_location,
    kb_run_feel, kb_runs, kb_self_level, kb_skip, kb_strength_frequency,
    kb_structure, kb_timezone, kb_volume,
)
from handlers.utils import safe_answer
from services.user_service import UserService

router = Router()


class OnboardingStates(StatesGroup):
    # Блок 1 — профиль
    last_name = State()
    first_name = State()
    middle_name = State()
    gender = State()
    birth_date = State()
    country = State()
    city = State()
    district = State()
    timezone = State()
    # Блок 2 — цель
    q_goal = State()
    # Блок 3 — текущий уровень
    q_runs = State()
    q_frequency = State()
    q_volume = State()
    q_longest_run = State()
    q_structure = State()
    # Блок 4 — опыт
    q_experience = State()
    q_break = State()
    # Блок 5 — ощущения (только если бегает)
    q_run_feel = State()
    # Блок 6 — боль
    q_pain = State()
    q_pain_location = State()
    q_pain_increases = State()
    q_injury_history = State()
    # Блок 7 — физическая форма
    q_other_sports = State()
    q_strength_frequency = State()
    q_location = State()
    # Блок 8 — самооценка
    q_self_level = State()


# ── Блок 1: Фамилия ───────────────────────────────────────────────────────────

@router.message(OnboardingStates.last_name)
async def step_last_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введи настоящую фамилию.")
        return

    user_svc = UserService(session)
    user, _ = await user_svc.get_or_create(message.from_user.id, full_name=name)
    await user_svc.update(user, last_name=name, full_name=name)

    await state.update_data(last_name=name)
    await state.set_state(OnboardingStates.first_name)
    await message.answer("Введи своё <b>имя</b>:", parse_mode="HTML")


# ── Блок 1: Имя ───────────────────────────────────────────────────────────────

@router.message(OnboardingStates.first_name)
async def step_first_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введи настоящее имя.")
        return

    await state.update_data(first_name=name)
    await state.set_state(OnboardingStates.middle_name)
    await message.answer(
        "Введи <b>отчество</b> (или пропусти):",
        parse_mode="HTML",
        reply_markup=kb_skip("onb:skip:middle_name"),
    )


# ── Блок 1: Отчество ──────────────────────────────────────────────────────────

@router.message(OnboardingStates.middle_name)
async def step_middle_name_text(message: Message, state: FSMContext) -> None:
    await state.update_data(middle_name=message.text.strip())
    await _ask_gender(message, state)


@router.callback_query(OnboardingStates.middle_name, F.data == "onb:skip:middle_name")
async def step_middle_name_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(middle_name=None)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await _ask_gender(callback.message, state)


async def _ask_gender(target, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.gender)
    await target.answer("Укажи <b>пол</b>:", parse_mode="HTML", reply_markup=kb_gender())


# ── Блок 1: Пол ───────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.gender, F.data.startswith("onb:gender:"))
async def step_gender(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(gender=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.birth_date)
    await callback.message.answer(
        "Укажи <b>дату рождения</b> в формате ДД.ММ.ГГГГ:",
        parse_mode="HTML",
    )


# ── Блок 1: Дата рождения ─────────────────────────────────────────────────────

@router.message(OnboardingStates.birth_date)
async def step_birth_date(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    try:
        day, month, year = text.split(".")
        birth = date(int(year), int(month), int(day))
    except Exception:
        await message.answer("Неверный формат. Введи как ДД.ММ.ГГГГ, например 15.06.1990:")
        return

    await state.update_data(birth_date=birth.isoformat())
    await state.set_state(OnboardingStates.country)
    await message.answer("В какой <b>стране</b> ты живёшь?", parse_mode="HTML")


# ── Блок 1: Страна ────────────────────────────────────────────────────────────

@router.message(OnboardingStates.country)
async def step_country(message: Message, state: FSMContext) -> None:
    await state.update_data(country=message.text.strip())
    await state.set_state(OnboardingStates.city)
    await message.answer("В каком <b>городе</b>?", parse_mode="HTML")


# ── Блок 1: Город ─────────────────────────────────────────────────────────────

@router.message(OnboardingStates.city)
async def step_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=message.text.strip())
    await state.set_state(OnboardingStates.district)
    await message.answer(
        "Укажи <b>район</b> (или пропусти):",
        parse_mode="HTML",
        reply_markup=kb_skip("onb:skip:district"),
    )


# ── Блок 1: Район ─────────────────────────────────────────────────────────────

@router.message(OnboardingStates.district)
async def step_district_text(message: Message, state: FSMContext) -> None:
    await state.update_data(district=message.text.strip())
    await _ask_timezone(message, state)


@router.callback_query(OnboardingStates.district, F.data == "onb:skip:district")
async def step_district_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(district=None)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await _ask_timezone(callback.message, state)


async def _ask_timezone(target, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.timezone)
    await target.answer(
        "Выбери свой <b>часовой пояс</b>:",
        parse_mode="HTML",
        reply_markup=kb_timezone(),
    )


# ── Блок 1: Часовой пояс ─────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.timezone, F.data.startswith("onb:tz:"))
async def step_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    offset = int(callback.data.split(":")[2])
    await state.update_data(timezone_offset=offset)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_goal)
    await callback.message.answer(
        "Отлично! Теперь несколько вопросов о беге.\n\n"
        "<b>Какая у тебя основная цель?</b>",
        parse_mode="HTML",
        reply_markup=kb_goal(),
    )


# ── Блок 2: Цель ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_goal, F.data.startswith("onb:goal:"))
async def step_q_goal(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_goal=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_runs)
    await callback.message.answer(
        "<b>Ты бегаешь сейчас?</b>",
        parse_mode="HTML",
        reply_markup=kb_runs(),
    )


# ── Блок 3: Бегает? ───────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_runs, F.data.startswith("onb:runs:"))
async def step_q_runs(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]  # no / irregular / regular
    runs = value != "no"
    await state.update_data(q_runs=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if not runs:
        await state.update_data(
            q_frequency="0_1",
            q_volume="to_10",
            q_longest_run=None,
            q_structure="no",
        )
        await state.set_state(OnboardingStates.q_experience)
        await callback.message.answer(
            "<b>Как давно ты занимаешься бегом?</b>",
            parse_mode="HTML",
            reply_markup=kb_experience(),
        )
    else:
        await state.set_state(OnboardingStates.q_frequency)
        await callback.message.answer(
            "<b>Как часто ты бегаешь?</b>",
            parse_mode="HTML",
            reply_markup=kb_frequency(),
        )


# ── Блок 3: Частота ───────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_frequency, F.data.startswith("onb:frequency:"))
async def step_q_frequency(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_frequency=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_volume)
    await callback.message.answer(
        "<b>Сколько км в неделю ты пробегаешь?</b>",
        parse_mode="HTML",
        reply_markup=kb_volume(),
    )


# ── Блок 3: Объём ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_volume, F.data.startswith("onb:volume:"))
async def step_q_volume(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_volume=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_longest_run)
    await callback.message.answer(
        "<b>Какой самый длинный бег за последнее время?</b>",
        parse_mode="HTML",
        reply_markup=kb_longest_run(),
    )


# ── Блок 3: Самый длинный бег ─────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_longest_run, F.data.startswith("onb:longest:"))
async def step_q_longest_run(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_longest_run=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_structure)
    await callback.message.answer(
        "<b>Есть ли у тебя план или система в тренировках?</b>",
        parse_mode="HTML",
        reply_markup=kb_structure(),
    )


# ── Блок 3: Структура (для алгоритма) ────────────────────────────────────────

@router.callback_query(OnboardingStates.q_structure, F.data.startswith("onb:structure:"))
async def step_q_structure(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_structure=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_experience)
    await callback.message.answer(
        "<b>Как давно ты занимаешься бегом?</b>",
        parse_mode="HTML",
        reply_markup=kb_experience(),
    )


# ── Блок 4: Опыт ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_experience, F.data.startswith("onb:exp:"))
async def step_q_experience(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_experience=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_break)
    await callback.message.answer(
        "<b>Был ли перерыв в беге?</b>",
        parse_mode="HTML",
        reply_markup=kb_break(),
    )


# ── Блок 4: Перерыв ───────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_break, F.data.startswith("onb:break:"))
async def step_q_break(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]  # no / to_1m / 1_3m / 3_6m / 6plus
    had_break = value != "no"
    await state.update_data(
        q_break_duration=value,
        q_break="yes" if had_break else "no",
    )
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    data = await state.get_data()
    runs = data.get("q_runs", "no") != "no"

    if runs:
        await state.set_state(OnboardingStates.q_run_feel)
        await callback.message.answer(
            "<b>Как тебе даётся бег?</b>",
            parse_mode="HTML",
            reply_markup=kb_run_feel(),
        )
    else:
        await state.set_state(OnboardingStates.q_pain)
        await callback.message.answer(
            "<b>Есть ли сейчас боли или дискомфорт в ногах / суставах?</b>",
            parse_mode="HTML",
            reply_markup=kb_pain(),
        )


# ── Блок 5: Как даётся бег ───────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_run_feel, F.data.startswith("onb:feel:"))
async def step_q_run_feel(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_run_feel=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_pain)
    await callback.message.answer(
        "<b>Есть ли сейчас боли или дискомфорт при беге / после?</b>",
        parse_mode="HTML",
        reply_markup=kb_pain(),
    )


# ── Блок 6: Боль ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_pain, F.data.startswith("onb:pain:"))
async def step_q_pain(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]  # none / little / yes
    await state.update_data(q_pain=value, q_pain_location_list=[])
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if value == "none":
        await state.update_data(
            q_pain_increases="no",
            q_pain_location=None,
            q_injury_history=None,
        )
        await _ask_other_sports(callback.message, state)
    else:
        await state.set_state(OnboardingStates.q_pain_location)
        await callback.message.answer(
            "<b>Где чаще всего возникает дискомфорт?</b>\n"
            "Можно выбрать несколько вариантов.",
            parse_mode="HTML",
            reply_markup=kb_pain_location([]),
        )


# ── Блок 6: Локализация боли (мультиселект) ───────────────────────────────────

@router.callback_query(OnboardingStates.q_pain_location, F.data.startswith("onb:pain_loc:"))
async def step_q_pain_location(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    data = await state.get_data()
    selected: list[str] = data.get("q_pain_location_list", [])

    if value == "done":
        await state.update_data(q_pain_location=",".join(selected) if selected else None)
        await callback.message.edit_reply_markup()
        await safe_answer(callback)
        await state.set_state(OnboardingStates.q_pain_increases)
        await callback.message.answer(
            "<b>Усиливается ли боль при нагрузке?</b>",
            parse_mode="HTML",
            reply_markup=kb_pain_increases(),
        )
        return

    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)

    await state.update_data(q_pain_location_list=selected)
    await callback.message.edit_reply_markup(reply_markup=kb_pain_location(selected))
    await safe_answer(callback)


# ── Блок 6: Боль при нагрузке ────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_pain_increases, F.data.startswith("onb:pain_inc:"))
async def step_q_pain_increases(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_pain_increases=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_injury_history)
    await callback.message.answer(
        "<b>Были ли травмы за последний год?</b>",
        parse_mode="HTML",
        reply_markup=kb_injury_history(),
    )


# ── Блок 6: История травм ─────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_injury_history, F.data.startswith("onb:injury:"))
async def step_q_injury_history(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_injury_history=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await _ask_other_sports(callback.message, state)


# ── Блок 7: Другой спорт (мультиселект) ──────────────────────────────────────

async def _ask_other_sports(target, state: FSMContext) -> None:
    await state.update_data(q_other_sports_list=[])
    await state.set_state(OnboardingStates.q_other_sports)
    await target.answer(
        "<b>Занимаешься ли чем-то кроме бега?</b>\n"
        "Можно выбрать несколько вариантов.",
        parse_mode="HTML",
        reply_markup=kb_other_sports([]),
    )


@router.callback_query(OnboardingStates.q_other_sports, F.data.startswith("onb:sports:"))
async def step_q_other_sports(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    data = await state.get_data()
    selected: list[str] = data.get("q_other_sports_list", [])

    if value == "done":
        await state.update_data(q_other_sports=",".join(selected) if selected else "none")
        await callback.message.edit_reply_markup()
        await safe_answer(callback)
        await state.set_state(OnboardingStates.q_strength_frequency)
        await callback.message.answer(
            "<b>Делаешь ли силовые тренировки?</b>",
            parse_mode="HTML",
            reply_markup=kb_strength_frequency(),
        )
        return

    if value == "none":
        selected = ["none"]
    else:
        if "none" in selected:
            selected.remove("none")
        if value in selected:
            selected.remove(value)
        else:
            selected.append(value)

    await state.update_data(q_other_sports_list=selected)
    await callback.message.edit_reply_markup(reply_markup=kb_other_sports(selected))
    await safe_answer(callback)


# ── Блок 7: Частота силовых ───────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_strength_frequency, F.data.startswith("onb:str_freq:"))
async def step_q_strength_frequency(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_strength_frequency=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_location)
    await callback.message.answer(
        "<b>Где планируешь делать силовые тренировки?</b>",
        parse_mode="HTML",
        reply_markup=kb_location(),
    )


# ── Блок 7: Место силовых ─────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_location, F.data.startswith("onb:location:"))
async def step_q_location(callback: CallbackQuery, state: FSMContext) -> None:
    location = callback.data.split(":")[2]
    await state.update_data(q_location=location)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_self_level)
    await callback.message.answer(
        "<b>Как ты оцениваешь свой уровень как бегун?</b>",
        parse_mode="HTML",
        reply_markup=kb_self_level(),
    )


# ── Блок 8: Самооценка → финал ────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_self_level, F.data.startswith("onb:self_lvl:"))
async def step_q_self_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_self_level=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    data = await state.get_data()
    await state.clear()

    runs = data.get("q_runs", "no") not in ("no", None)
    structure = data.get("q_structure", "no") == "yes"
    had_break = data.get("q_break", "no") == "yes"
    location = data.get("q_location", "home")

    answers = OnboardingAnswers(
        runs=runs,
        frequency=data.get("q_frequency", "0_1"),
        volume=data.get("q_volume", "to_10"),
        structure=structure,
        had_break=had_break,
        pain=data.get("q_pain", "none"),
        pain_increases=data.get("q_pain_increases", "no"),
        location=location,
    )
    level = assign_level(answers)

    level_names = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}

    last_name = data.get("last_name", "")
    first_name = data.get("first_name", "")
    middle_name = data.get("middle_name") or ""
    full_name = f"{last_name} {first_name} {middle_name}".strip()

    birth_date = date.fromisoformat(data["birth_date"]) if data.get("birth_date") else None

    user_svc = UserService(session)
    user = await user_svc.get_or_raise(callback.from_user.id)

    await user_svc.update(
        user,
        full_name=full_name,
        last_name=last_name or None,
        first_name=first_name or None,
        middle_name=data.get("middle_name"),
        gender=data.get("gender"),
        birth_date=birth_date,
        country=data.get("country"),
        city=data.get("city"),
        district=data.get("district"),
        timezone_offset=data.get("timezone_offset", 3),
        level=level,
        strength_format=location,
        program_start_date=None,
        onboarding_complete=True,
        status="pending",
        # Блок 2
        q_goal=data.get("q_goal"),
        # Блок 3
        q_runs=data.get("q_runs"),
        q_frequency=data.get("q_frequency"),
        q_volume=data.get("q_volume"),
        q_longest_run=data.get("q_longest_run"),
        q_structure=data.get("q_structure"),
        # Блок 4
        q_experience=data.get("q_experience"),
        q_break=data.get("q_break"),
        q_break_duration=data.get("q_break_duration"),
        # Блок 5
        q_run_feel=data.get("q_run_feel"),
        # Блок 6
        q_pain=data.get("q_pain"),
        q_pain_location=data.get("q_pain_location"),
        q_pain_increases=data.get("q_pain_increases"),
        q_injury_history=data.get("q_injury_history"),
        # Блок 7
        q_other_sports=data.get("q_other_sports"),
        q_strength_frequency=data.get("q_strength_frequency"),
        # Блок 8
        q_self_level=data.get("q_self_level"),
    )

    await callback.message.answer(
        "✅ <b>Анкета заполнена!</b>\n\n"
        "Я сохранил твои данные.\n"
        "Тренер проверит анкету и назначит тебе тренировочный план.",
        parse_mode="HTML",
    )

    # ── Уведомление тренеру ───────────────────────────────────────────────────
    tg_link = f"@{callback.from_user.username}" if callback.from_user.username else f"id:{callback.from_user.id}"

    goal_labels = {
        "start_zero": "Начать с нуля",
        "return":     "Вернуться после перерыва",
        "distance":   "Пробежать дистанцию",
        "improve":    "Улучшить результат",
        "no_pain":    "Бегать без боли",
        "health":     "Общее здоровье и форма",
    }
    runs_labels    = {"no": "Нет", "irregular": "Нерегулярно", "regular": "Регулярно"}
    freq_labels    = {"0_1": "0–1 р/нед", "2_3": "2–3 р/нед", "4plus": "4+ р/нед"}
    vol_labels     = {"to_10": "до 10 км", "10_25": "10–25 км", "25_50": "25–50 км", "50plus": "50+ км"}
    longest_labels = {"to_5": "до 5 км", "5_10": "5–10 км", "10_15": "10–15 км", "15plus": "15+ км"}
    exp_labels     = {"beginner": "Только начинаю", "to_6m": "до 6 мес", "6_12m": "6–12 мес", "1_3y": "1–3 года", "3plus": "3+ лет"}
    break_labels   = {"no": "Нет", "to_1m": "до 1 мес", "1_3m": "1–3 мес", "3_6m": "3–6 мес", "6plus": "6+ мес"}
    feel_labels    = {"hard": "Тяжело", "medium": "Нормально", "easy": "Комфортно"}
    pain_labels    = {"none": "Нет", "little": "Иногда", "yes": "Регулярно"}
    pain_inc_lbl   = {"no": "Нет", "yes": "Усиливается", "not_sure": "Не уверен(а)"}
    str_freq_lbl   = {"no": "Не делаю", "sometimes": "Иногда", "regularly": "Регулярно"}
    self_lbl       = {"beginner": "Новичок", "base": "Базовый", "medium": "Средний", "advanced": "Продвинутый"}
    gender_lbl     = {"m": "Мужской", "f": "Женский"}

    pain_loc = data.get("q_pain_location") or "—"
    sports   = data.get("q_other_sports") or "—"

    admin_text = (
        f"👤 <b>Новый пользователь ждёт подтверждения!</b>\n\n"
        f"Имя: <b>{full_name}</b>\n"
        f"Telegram: {tg_link}\n"
        f"ID: <code>{callback.from_user.id}</code>\n"
        f"Пол: {gender_lbl.get(data.get('gender', ''), '—')}\n\n"
        f"<b>Цель:</b> {goal_labels.get(data.get('q_goal', ''), '—')}\n\n"
        f"<b>Бег:</b>\n"
        f"• Бегает: {runs_labels.get(data.get('q_runs', 'no'), '—')}\n"
        f"• Частота: {freq_labels.get(data.get('q_frequency', ''), '—')}\n"
        f"• Объём: {vol_labels.get(data.get('q_volume', ''), '—')}\n"
        f"• Самый длинный: {longest_labels.get(data.get('q_longest_run', ''), '—')}\n"
        f"• Как даётся: {feel_labels.get(data.get('q_run_feel', ''), '—')}\n\n"
        f"<b>Опыт:</b>\n"
        f"• Стаж: {exp_labels.get(data.get('q_experience', ''), '—')}\n"
        f"• Перерыв: {break_labels.get(data.get('q_break_duration', 'no'), '—')}\n\n"
        f"<b>Здоровье:</b>\n"
        f"• Боль: {pain_labels.get(data.get('q_pain', 'none'), '—')}\n"
        f"• Где: {pain_loc}\n"
        f"• Усиливается: {pain_inc_lbl.get(data.get('q_pain_increases', 'no'), '—')}\n"
        f"• Травмы за год: {'Да' if data.get('q_injury_history') == 'yes' else 'Нет'}\n\n"
        f"<b>Физическая форма:</b>\n"
        f"• Другой спорт: {sports}\n"
        f"• Силовые: {str_freq_lbl.get(data.get('q_strength_frequency', ''), '—')}\n"
        f"• Силовые где: {'🏋️ Зал' if location == 'gym' else '🏠 Дома'}\n\n"
        f"<b>Самооценка:</b> {self_lbl.get(data.get('q_self_level', ''), '—')}\n\n"
        f"🤖 Автоматический уровень: <b>{level_names[level]} ({level})</b>"
    )

    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=kb_admin_approve(callback.from_user.id, level),
            )
        except Exception:
            pass
