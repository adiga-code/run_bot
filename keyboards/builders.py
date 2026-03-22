from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.timezones import TIMEZONES


# ── Onboarding ────────────────────────────────────────────────────────────────

def kb_runs() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, бегаю", callback_data="onb:runs:yes")
    builder.button(text="❌ Нет, не бегаю", callback_data="onb:runs:no")
    builder.adjust(1)
    return builder.as_markup()


def kb_frequency() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="0–1 раз в неделю", callback_data="onb:frequency:0_1")
    builder.button(text="2–3 раза в неделю", callback_data="onb:frequency:2_3")
    builder.button(text="4+ раза в неделю", callback_data="onb:frequency:4plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_volume() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Не бегаю / до 10 км/нед", callback_data="onb:volume:to_10")
    builder.button(text="10–25 км/нед", callback_data="onb:volume:10_25")
    builder.button(text="25–50 км/нед", callback_data="onb:volume:25_50")
    builder.button(text="50+ км/нед", callback_data="onb:volume:50plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_structure() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, есть план / система", callback_data="onb:structure:yes")
    builder.button(text="❌ Нет, бегаю как получается", callback_data="onb:structure:no")
    builder.adjust(1)
    return builder.as_markup()


def kb_break() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Нет, бегаю без перерывов", callback_data="onb:break:no")
    builder.button(text="⚠️ Да, был перерыв", callback_data="onb:break:yes")
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


# ── Admin approval ────────────────────────────────────────────────────────────

def kb_apply() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Подать заявку", callback_data="app:start")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_application(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"adm:app:approve:{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"adm:app:reject:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def kb_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏳ Ожидающие подтверждения", callback_data="adm:menu:pending")
    builder.button(text="👥 Все пользователи", callback_data="adm:menu:users")
    builder.button(text="📋 Отчёты", callback_data="adm:menu:reports")
    builder.button(text="📊 Статистика", callback_data="adm:menu:stats")
    builder.button(text="🔒 Whitelist", callback_data="adm:menu:whitelist")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_report_users(users: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users:
        builder.button(text=u.full_name, callback_data=f"adm:report:view:{u.telegram_id}")
    builder.button(text="◀️ Назад", callback_data="adm:menu:back")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_report_actions(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Скачать CSV", callback_data=f"adm:report:csv:{user_id}")
    builder.button(text="⚙️ Управление", callback_data=f"adm:manage:{user_id}")
    builder.button(text="◀️ К списку", callback_data="adm:menu:reports")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_manage(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Изменить режим дня", callback_data=f"adm:mode:{user_id}")
    builder.button(text="⏭️ Перейти к дню", callback_data=f"adm:jump:{user_id}")
    builder.button(text="🎯 Изменить уровень", callback_data=f"adm:pick:{user_id}")
    builder.button(text="✉️ Отправить сообщение", callback_data=f"adm:msg:{user_id}")
    builder.button(text="◀️ Назад", callback_data=f"adm:report:view:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_day_mode(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💪 Base (полная)", callback_data=f"adm:mode:set:{user_id}:base")
    builder.button(text="🔆 Light (лёгкая)", callback_data=f"adm:mode:set:{user_id}:light")
    builder.button(text="🔄 Recovery (восстановление)", callback_data=f"adm:mode:set:{user_id}:recovery")
    builder.button(text="◀️ Назад", callback_data=f"adm:manage:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_approve(user_id: int, level: int) -> InlineKeyboardMarkup:
    """Sent to admin when a new user completes onboarding."""
    level_names = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}
    name = level_names[level]
    builder = InlineKeyboardBuilder()
    builder.button(text=f"▶️ Старт сегодня ({level} — {name})", callback_data=f"adm:approve:today:{user_id}:{level}")
    builder.button(text=f"📅 Старт завтра ({level} — {name})", callback_data=f"adm:approve:tomorrow:{user_id}:{level}")
    builder.button(text="✏️ Изменить уровень", callback_data=f"adm:pick:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_start_choice(user_id: int, level: int) -> InlineKeyboardMarkup:
    """After admin picks a custom level — choose start date."""
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Старт сегодня", callback_data=f"adm:approve:today:{user_id}:{level}")
    builder.button(text="📅 Старт завтра", callback_data=f"adm:approve:tomorrow:{user_id}:{level}")
    builder.adjust(2)
    return builder.as_markup()


def kb_admin_level_picker(user_id: int) -> InlineKeyboardMarkup:
    """Level selector for admin to override auto-detected level."""
    level_names = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}
    builder = InlineKeyboardBuilder()
    for lvl, name in level_names.items():
        builder.button(text=f"{lvl} — {name}", callback_data=f"adm:setlvl:{user_id}:{lvl}")
    builder.adjust(1)
    return builder.as_markup()


# ── Evening reminder mark button ──────────────────────────────────────────────

def kb_mark_workout() -> InlineKeyboardMarkup:
    """Single button for evening reminder — triggers the completion FSM."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отметить тренировку", callback_data="wk:mark")
    builder.adjust(1)
    return builder.as_markup()


# ── Strength day options ──────────────────────────────────────────────────────

def kb_strength_day_options() -> InlineKeyboardMarkup:
    """Shown after strength workout is displayed: mark it or do a custom workout."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отметить тренировку", callback_data="wk:mark")
    builder.button(text="🔄 Сделаю свою тренировку", callback_data="wk:custom")
    builder.button(text="📊 Мой прогресс", callback_data="menu:progress")
    builder.button(text="🔔 Напоминания", callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


# ── Progress / Main menu ──────────────────────────────────────────────────────

def kb_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Сегодняшняя тренировка", callback_data="menu:today")
    builder.button(text="📊 Мой прогресс", callback_data="menu:progress")
    builder.button(text="🔔 Напоминания", callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


def kb_progress_menu() -> InlineKeyboardMarkup:
    """Progress view with reset day option."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Начать день заново", callback_data="menu:reset_day")
    builder.button(text="📋 Сегодняшняя тренировка", callback_data="menu:today")
    builder.button(text="🔔 Напоминания", callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


def kb_reschedule() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Перенести тренировку", callback_data="wk:reschedule")
    builder.button(text="Оставить как есть", callback_data="wk:keep")
    builder.adjust(1)
    return builder.as_markup()
