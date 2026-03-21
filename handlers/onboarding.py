from datetime import date

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from engine.level_assignment import OnboardingAnswers, assign_level
from keyboards.builders import (
    kb_break, kb_frequency, kb_location, kb_pain,
    kb_pain_increases, kb_regularity, kb_strength, kb_timezone, kb_volume,
)
from services.user_service import UserService
from keyboards.builders import kb_main_menu

router = Router()


class OnboardingStates(StatesGroup):
    full_name = State()
    birth_date = State()
    country = State()
    city = State()
    district = State()
    timezone = State()
    q_frequency = State()
    q_volume = State()
    q_regularity = State()
    q_break = State()
    q_pain = State()
    q_pain_increases = State()
    q_strength = State()
    q_location = State()


# ── Entry point (triggered from start.py) ────────────────────────────────────

@router.message(CommandStart())
async def onboarding_entry(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Only handles /start for users who need onboarding (not yet complete)."""
    user_svc = UserService(session)
    user = await user_svc.get(message.from_user.id)

    if user and user.onboarding_complete:
        return  # handled by start.py

    await state.set_state(OnboardingStates.full_name)
    await message.answer(
        "👋 Привет! Я твой беговой помощник на 28 дней.\n\n"
        "Давай познакомимся. Напиши своё <b>полное имя</b> (ФИО одним сообщением):",
        parse_mode="HTML",
    )


# ── Step 1: ФИО ───────────────────────────────────────────────────────────────

@router.message(OnboardingStates.full_name)
async def step_full_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введи настоящее имя.")
        return

    user_svc = UserService(session)
    user, _ = await user_svc.get_or_create(message.from_user.id, full_name=name)
    await user_svc.update(user, full_name=name)

    await state.update_data(full_name=name)
    await state.set_state(OnboardingStates.birth_date)
    await message.answer("Отлично! Теперь укажи <b>дату рождения</b> в формате ДД.ММ.ГГГГ:", parse_mode="HTML")


# ── Step 2: Дата рождения ─────────────────────────────────────────────────────

@router.message(OnboardingStates.birth_date)
async def step_birth_date(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    try:
        day, month, year = text.split(".")
        birth = date(int(year), int(month), int(day))
    except Exception:
        await message.answer("Неверный формат. Введи дату как ДД.ММ.ГГГГ, например 15.06.1990:")
        return

    await state.update_data(birth_date=birth.isoformat())
    await state.set_state(OnboardingStates.country)
    await message.answer("Отлично! В какой <b>стране</b> ты живёшь?", parse_mode="HTML")


# ── Step 3: Страна ────────────────────────────────────────────────────────────

@router.message(OnboardingStates.country)
async def step_country(message: Message, state: FSMContext) -> None:
    await state.update_data(country=message.text.strip())
    await state.set_state(OnboardingStates.city)
    await message.answer("В каком <b>городе</b>?", parse_mode="HTML")


# ── Step 4: Город ─────────────────────────────────────────────────────────────

@router.message(OnboardingStates.city)
async def step_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=message.text.strip())
    await state.set_state(OnboardingStates.district)
    await message.answer("Укажи <b>район</b> (или напиши «—» если не важно):", parse_mode="HTML")


# ── Step 5: Район ─────────────────────────────────────────────────────────────

@router.message(OnboardingStates.district)
async def step_district(message: Message, state: FSMContext) -> None:
    district = message.text.strip()
    if district == "—":
        district = None
    await state.update_data(district=district)
    await state.set_state(OnboardingStates.timezone)
    await message.answer(
        "Выбери свой <b>часовой пояс</b>:",
        parse_mode="HTML",
        reply_markup=kb_timezone(),
    )


# ── Step 6: Часовой пояс ─────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.timezone, F.data.startswith("onb:tz:"))
async def step_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    offset = int(callback.data.split(":")[2])
    await state.update_data(timezone_offset=offset)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_frequency)
    await callback.message.answer(
        "Теперь несколько вопросов о твоей беговой подготовке.\n\n"
        "<b>Как часто ты бегаешь?</b>",
        parse_mode="HTML",
        reply_markup=kb_frequency(),
    )


# ── Step 7-14: 8 вопросов о подготовке ──────────────────────────────────────

@router.callback_query(OnboardingStates.q_frequency, F.data.startswith("onb:frequency:"))
async def step_q_frequency(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_frequency=value)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_volume)
    await callback.message.answer("<b>Сколько примерно бегаешь в неделю?</b>", parse_mode="HTML", reply_markup=kb_volume())


@router.callback_query(OnboardingStates.q_volume, F.data.startswith("onb:volume:"))
async def step_q_volume(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_volume=value)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_regularity)
    await callback.message.answer("<b>Есть ли система в тренировках?</b>", parse_mode="HTML", reply_markup=kb_regularity())


@router.callback_query(OnboardingStates.q_regularity, F.data.startswith("onb:regularity:"))
async def step_q_regularity(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_regularity=value)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_break)
    await callback.message.answer("<b>Был ли перерыв в беге?</b>", parse_mode="HTML", reply_markup=kb_break())


@router.callback_query(OnboardingStates.q_break, F.data.startswith("onb:break:"))
async def step_q_break(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_break=value)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_pain)
    await callback.message.answer("<b>Есть ли сейчас боли при беге или после?</b>", parse_mode="HTML", reply_markup=kb_pain())


@router.callback_query(OnboardingStates.q_pain, F.data.startswith("onb:pain:"))
async def step_q_pain(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_pain=value)
    await callback.message.edit_reply_markup()
    await callback.answer()

    if value == "none":
        # Skip pain_increases question
        await state.update_data(q_pain_increases="no")
        await state.set_state(OnboardingStates.q_strength)
        await callback.message.answer("<b>Занимаешься ли силовыми тренировками?</b>", parse_mode="HTML", reply_markup=kb_strength())
    else:
        await state.set_state(OnboardingStates.q_pain_increases)
        await callback.message.answer("<b>Усиливается ли боль под нагрузкой?</b>", parse_mode="HTML", reply_markup=kb_pain_increases())


@router.callback_query(OnboardingStates.q_pain_increases, F.data.startswith("onb:pain_inc:"))
async def step_q_pain_increases(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_pain_increases=value)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_strength)
    await callback.message.answer("<b>Занимаешься ли силовыми тренировками?</b>", parse_mode="HTML", reply_markup=kb_strength())


@router.callback_query(OnboardingStates.q_strength, F.data.startswith("onb:strength:"))
async def step_q_strength(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_strength=value)
    await callback.message.edit_reply_markup()
    await callback.answer()
    await state.set_state(OnboardingStates.q_location)
    await callback.message.answer("<b>Где планируешь делать силовые?</b>", parse_mode="HTML", reply_markup=kb_location())


@router.callback_query(OnboardingStates.q_location, F.data.startswith("onb:location:"))
async def step_q_location(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    location = callback.data.split(":")[2]
    await state.update_data(q_location=location)
    await callback.message.edit_reply_markup()
    await callback.answer()

    data = await state.get_data()
    await state.clear()

    # Compute level
    answers = OnboardingAnswers(
        frequency=data["q_frequency"],
        volume=data["q_volume"],
        regularity=data["q_regularity"],
        break_status=data["q_break"],
        pain=data["q_pain"],
        pain_increases=data["q_pain_increases"],
        strength=data["q_strength"],
        location=location,
    )
    level = assign_level(answers)

    level_names = {1: "Start", 2: "Return", 3: "Base", 4: "Stability"}

    # Save everything to DB
    user_svc = UserService(session)
    user = await user_svc.get_or_raise(callback.from_user.id)
    birth_date = date.fromisoformat(data["birth_date"]) if data.get("birth_date") else None

    await user_svc.update(
        user,
        full_name=data.get("full_name", user.full_name),
        birth_date=birth_date,
        country=data.get("country"),
        city=data.get("city"),
        district=data.get("district"),
        timezone_offset=data.get("timezone_offset", 3),
        level=level,
        strength_format=location,
        program_start_date=date.today(),
        onboarding_complete=True,
        q_frequency=data["q_frequency"],
        q_volume=data["q_volume"],
        q_regularity=data["q_regularity"],
        q_break=data["q_break"],
        q_pain=data["q_pain"],
        q_pain_increases=data["q_pain_increases"],
        q_strength=data["q_strength"],
    )

    await callback.message.answer(
        f"✅ Отлично! Анкета заполнена.\n\n"
        f"Твой уровень: <b>{level_names[level]} (уровень {level})</b>\n"
        f"Программа стартует <b>сегодня</b>! 🎉\n\n"
        f"Каждое утро я буду спрашивать о твоём самочувствии и показывать тренировку на день.\n"
        f"Первый чек-ин — прямо сейчас!",
        parse_mode="HTML",
        reply_markup=kb_main_menu(),
    )
