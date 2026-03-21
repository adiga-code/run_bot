from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.timezones import TIMEZONES


# ── Onboarding ────────────────────────────────────────────────────────────────

def kb_frequency() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Не бегаю совсем", callback_data="onb:frequency:not_at_all")
    builder.button(text="1 раз в неделю", callback_data="onb:frequency:once")
    builder.button(text="2-3 раза в неделю", callback_data="onb:frequency:2_3x")
    builder.button(text="4+ раза в неделю", callback_data="onb:frequency:4plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_volume() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Не бегаю", callback_data="onb:volume:none")
    builder.button(text="До 60 мин/нед", callback_data="onb:volume:up_to_60")
    builder.button(text="60-120 мин/нед", callback_data="onb:volume:60_to_120")
    builder.button(text="120+ мин/нед", callback_data="onb:volume:120plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_regularity() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Без системы", callback_data="onb:regularity:no_system")
    builder.button(text="Иногда", callback_data="onb:regularity:sometimes")
    builder.button(text="Регулярно", callback_data="onb:regularity:regularly")
    builder.adjust(1)
    return builder.as_markup()


def kb_break() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Давно не бегал(а)", callback_data="onb:break:long_break")
    builder.button(text="Был перерыв", callback_data="onb:break:had_break")
    builder.button(text="Без перерывов", callback_data="onb:break:no_break")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет боли", callback_data="onb:pain:none")
    builder.button(text="Небольшая боль", callback_data="onb:pain:little")
    builder.button(text="Да, есть боль", callback_data="onb:pain:yes")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain_increases() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет, не усиливается", callback_data="onb:pain_inc:no")
    builder.button(text="Да, усиливается", callback_data="onb:pain_inc:yes")
    builder.button(text="Не уверен(а)", callback_data="onb:pain_inc:not_sure")
    builder.adjust(1)
    return builder.as_markup()


def kb_strength() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Не делаю", callback_data="onb:strength:no")
    builder.button(text="Иногда", callback_data="onb:strength:sometimes")
    builder.button(text="Регулярно", callback_data="onb:strength:regularly")
    builder.adjust(1)
    return builder.as_markup()


def kb_location() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Дома", callback_data="onb:location:home")
    builder.button(text="🏋️ В зале", callback_data="onb:location:gym")
    builder.adjust(2)
    return builder.as_markup()


def kb_timezone() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tz in TIMEZONES:
        builder.button(
            text=tz["label"],
            callback_data=f"onb:tz:{tz['offset']}",
        )
    builder.adjust(1)
    return builder.as_markup()


# ── Check-in ──────────────────────────────────────────────────────────────────

def kb_wellbeing() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="😞 Плохо", callback_data="ci:wellbeing:1")
    builder.button(text="😤 Тяжеловато", callback_data="ci:wellbeing:2")
    builder.button(text="😐 Нормально", callback_data="ci:wellbeing:3")
    builder.button(text="😊 Отлично", callback_data="ci:wellbeing:4")
    builder.adjust(2)
    return builder.as_markup()


def kb_stress() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Нет", callback_data="ci:stress:1")
    builder.button(text="⚡ Умеренный", callback_data="ci:stress:2")
    builder.button(text="🌪 Сильный", callback_data="ci:stress:3")
    builder.adjust(3)
    return builder.as_markup()


def kb_sleep() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="😴 Плохо", callback_data="ci:sleep:1")
    builder.button(text="😐 Нормально", callback_data="ci:sleep:2")
    builder.button(text="💤 Отлично", callback_data="ci:sleep:3")
    builder.adjust(3)
    return builder.as_markup()


def kb_pain_checkin() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Нет боли", callback_data="ci:pain:1")
    builder.button(text="⚠️ Немного", callback_data="ci:pain:2")
    builder.button(text="🛑 Да, болит", callback_data="ci:pain:3")
    builder.adjust(3)
    return builder.as_markup()


def kb_pain_increases_checkin() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет", callback_data="ci:pain_inc:no")
    builder.button(text="Да", callback_data="ci:pain_inc:yes")
    builder.button(text="Не уверен(а)", callback_data="ci:pain_inc:not_sure")
    builder.adjust(2)
    return builder.as_markup()


# ── Workout completion ────────────────────────────────────────────────────────

def kb_completion() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнено", callback_data="wk:status:done")
    builder.button(text="⚡ Частично", callback_data="wk:status:partial")
    builder.button(text="❌ Пропустил(а)", callback_data="wk:status:skipped")
    builder.adjust(1)
    return builder.as_markup()


def kb_effort() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        labels = {1: "1 — легко", 2: "2", 3: "3 — средне", 4: "4", 5: "5 — очень тяжело"}
        builder.button(text=labels[i], callback_data=f"wk:effort:{i}")
    builder.adjust(5)
    return builder.as_markup()


def kb_had_pain() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет боли", callback_data="wk:pain:no")
    builder.button(text="Была боль", callback_data="wk:pain:yes")
    builder.adjust(2)
    return builder.as_markup()


# ── Progress / Main menu ──────────────────────────────────────────────────────

def kb_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Сегодняшняя тренировка", callback_data="menu:today")
    builder.button(text="📊 Мой прогресс", callback_data="menu:progress")
    builder.button(text="🔔 Напоминания", callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


def kb_reschedule() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Перенести тренировку", callback_data="wk:reschedule")
    builder.button(text="Оставить как есть", callback_data="wk:keep")
    builder.adjust(1)
    return builder.as_markup()
