from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from engine.level_assignment import OnboardingAnswers, assign_level
from keyboards.builders import (
    kb_break, kb_frequency, kb_location, kb_main_menu, kb_pain,
    kb_pain_increases, kb_runs, kb_structure, kb_timezone, kb_volume,
    kb_admin_approve,
)
from handlers.utils import safe_answer
from services.user_service import UserService

router = Router()


class OnboardingStates(StatesGroup):
    full_name = State()
    birth_date = State()
    country = State()
    city = State()
    district = State()
    timezone = State()
    q_runs = State()
    q_frequency = State()
    q_volume = State()
    q_structure = State()
    q_break = State()
    q_pain = State()
    q_pain_increases = State()
    q_location = State()


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
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_runs)
    await callback.message.answer(
        "Теперь несколько вопросов о твоей беговой подготовке.\n\n"
        "<b>Ты бегаешь?</b>",
        parse_mode="HTML",
        reply_markup=kb_runs(),
    )


# ── Step 7: Бегает? ───────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_runs, F.data.startswith("onb:runs:"))
async def step_q_runs(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]  # "yes" or "no"
    runs = value == "yes"
    await state.update_data(q_runs=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if not runs:
        # Skip running questions → go straight to location
        await state.update_data(
            q_frequency="0_1",
            q_volume="to_10",
            q_structure="no",
            q_break="no",
        )
        await state.set_state(OnboardingStates.q_pain)
        await callback.message.answer(
            "<b>Есть ли сейчас боли или дискомфорт в ногах / суставах?</b>",
            parse_mode="HTML",
            reply_markup=kb_pain(),
        )
    else:
        await state.set_state(OnboardingStates.q_frequency)
        await callback.message.answer(
            "<b>Как часто ты бегаешь?</b>",
            parse_mode="HTML",
            reply_markup=kb_frequency(),
        )


# ── Step 8: Частота ───────────────────────────────────────────────────────────

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


# ── Step 9: Объём ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_volume, F.data.startswith("onb:volume:"))
async def step_q_volume(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_volume=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_structure)
    await callback.message.answer(
        "<b>Есть ли у тебя план или система в тренировках?</b>",
        parse_mode="HTML",
        reply_markup=kb_structure(),
    )


# ── Step 10: Структура ────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_structure, F.data.startswith("onb:structure:"))
async def step_q_structure(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]  # "yes" or "no"
    await state.update_data(q_structure=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_break)
    await callback.message.answer(
        "<b>Был ли перерыв в беге (больше 2 недель)?</b>",
        parse_mode="HTML",
        reply_markup=kb_break(),
    )


# ── Step 11: Перерыв ──────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_break, F.data.startswith("onb:break:"))
async def step_q_break(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]  # "yes" or "no"
    await state.update_data(q_break=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_pain)
    await callback.message.answer(
        "<b>Есть ли сейчас боли или дискомфорт при беге / после?</b>",
        parse_mode="HTML",
        reply_markup=kb_pain(),
    )


# ── Step 12: Боль ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_pain, F.data.startswith("onb:pain:"))
async def step_q_pain(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_pain=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    if value == "none":
        await state.update_data(q_pain_increases="no")
        await state.set_state(OnboardingStates.q_location)
        await callback.message.answer(
            "<b>Где планируешь делать силовые тренировки?</b>",
            parse_mode="HTML",
            reply_markup=kb_location(),
        )
    else:
        await state.set_state(OnboardingStates.q_pain_increases)
        await callback.message.answer(
            "<b>Усиливается ли боль при нагрузке?</b>",
            parse_mode="HTML",
            reply_markup=kb_pain_increases(),
        )


# ── Step 13: Боль при нагрузке ────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_pain_increases, F.data.startswith("onb:pain_inc:"))
async def step_q_pain_increases(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[2]
    await state.update_data(q_pain_increases=value)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)
    await state.set_state(OnboardingStates.q_location)
    await callback.message.answer(
        "<b>Где планируешь делать силовые тренировки?</b>",
        parse_mode="HTML",
        reply_markup=kb_location(),
    )


# ── Step 14: Место силовых ────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.q_location, F.data.startswith("onb:location:"))
async def step_q_location(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    location = callback.data.split(":")[2]
    await state.update_data(q_location=location)
    await callback.message.edit_reply_markup()
    await safe_answer(callback)

    data = await state.get_data()
    await state.clear()

    runs = data.get("q_runs", "yes") == "yes"
    structure = data.get("q_structure", "no") == "yes"
    had_break = data.get("q_break", "no") == "yes"

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
        program_start_date=None,
        onboarding_complete=True,
        status="pending",
        q_runs=data.get("q_runs"),
        q_frequency=data.get("q_frequency"),
        q_volume=data.get("q_volume"),
        q_structure=data.get("q_structure"),
        q_break=data.get("q_break"),
        q_pain=data.get("q_pain"),
        q_pain_increases=data.get("q_pain_increases"),
    )

    await callback.message.answer(
        "✅ <b>Анкета заполнена!</b>\n\n"
        "Я проверю твои ответы и скоро подключу тебя к программе.\n\n"
        "⏳ Как только тренер подтвердит твой уровень — программа начнётся!",
        parse_mode="HTML",
    )

    # Notify all admins
    runs_label = "Да" if runs else "Нет"
    structure_label = "Да" if structure else "Нет"
    break_label = "Да" if had_break else "Нет"
    location_label = "🏠 Дома" if location == "home" else "🏋️ В зале"
    tg_link = f"@{callback.from_user.username}" if callback.from_user.username else f"id:{callback.from_user.id}"

    pain_labels = {"none": "Нет боли", "little": "Небольшая", "yes": "Есть боль"}
    pain_inc_labels = {"no": "Нет", "yes": "Усиливается", "not_sure": "Не уверен(а)"}
    freq_labels = {"0_1": "0–1 раз/нед", "2_3": "2–3 раза/нед", "4plus": "4+ раз/нед"}
    vol_labels = {"to_10": "до 10 км", "10_25": "10–25 км", "25_50": "25–50 км", "50plus": "50+ км"}

    admin_text = (
        f"👤 <b>Новый пользователь ждёт подтверждения!</b>\n\n"
        f"Имя: <b>{user.full_name}</b>\n"
        f"Telegram: {tg_link}\n"
        f"ID: <code>{callback.from_user.id}</code>\n\n"
        f"<b>Ответы анкеты:</b>\n"
        f"• Бегает: {runs_label}\n"
        f"• Частота: {freq_labels.get(data.get('q_frequency', '0_1'), '—')}\n"
        f"• Объём: {vol_labels.get(data.get('q_volume', 'to_10'), '—')}\n"
        f"• Система/план: {structure_label}\n"
        f"• Перерыв: {break_label}\n"
        f"• Боль: {pain_labels.get(data.get('q_pain', 'none'), '—')}\n"
        f"• Боль при нагрузке: {pain_inc_labels.get(data.get('q_pain_increases', 'no'), '—')}\n"
        f"• Силовые: {location_label}\n\n"
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
