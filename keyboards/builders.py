from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.timezones import TIMEZONES


# ── Onboarding ────────────────────────────────────────────────────────────────

def kb_skip(callback_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить →", callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()


def kb_gender() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Мужской", callback_data="onb:gender:m")
    builder.button(text="Женский", callback_data="onb:gender:f")
    builder.adjust(2)
    return builder.as_markup()


def kb_goal() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 Начать бегать с нуля",          callback_data="onb:goal:start_zero")
    builder.button(text="🔄 Вернуться после перерыва",       callback_data="onb:goal:return")
    builder.button(text="🏅 Пробежать дистанцию",            callback_data="onb:goal:distance")
    builder.button(text="⚡ Улучшить результат",             callback_data="onb:goal:improve")
    builder.button(text="🦵 Бегать без боли",                callback_data="onb:goal:no_pain")
    builder.button(text="💚 Общее здоровье и форма",         callback_data="onb:goal:health")
    builder.adjust(1)
    return builder.as_markup()


def kb_distance() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="5 км",           callback_data="onb:distance:5k")
    builder.button(text="10 км",          callback_data="onb:distance:10k")
    builder.button(text="Полумарафон",    callback_data="onb:distance:half")
    builder.button(text="Марафон",        callback_data="onb:distance:full")
    builder.button(text="Другая",         callback_data="onb:distance:other")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def kb_runs() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Нет",              callback_data="onb:runs:no")
    builder.button(text="🔄 Да, нерегулярно", callback_data="onb:runs:irregular")
    builder.button(text="✅ Да, регулярно",    callback_data="onb:runs:regular")
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


def kb_longest_run() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="До 5 км",   callback_data="onb:longest:to_5")
    builder.button(text="5–10 км",   callback_data="onb:longest:5_10")
    builder.button(text="10–15 км",  callback_data="onb:longest:10_15")
    builder.button(text="15+ км",    callback_data="onb:longest:15plus")
    builder.adjust(2)
    return builder.as_markup()


def kb_experience() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Только начинаю",  callback_data="onb:exp:beginner")
    builder.button(text="До 6 месяцев",    callback_data="onb:exp:to_6m")
    builder.button(text="6–12 месяцев",    callback_data="onb:exp:6_12m")
    builder.button(text="1–3 года",        callback_data="onb:exp:1_3y")
    builder.button(text="3+ лет",          callback_data="onb:exp:3plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_break() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет перерыва",   callback_data="onb:break:no")
    builder.button(text="До 1 месяца",    callback_data="onb:break:to_1m")
    builder.button(text="1–3 месяца",     callback_data="onb:break:1_3m")
    builder.button(text="3–6 месяцев",    callback_data="onb:break:3_6m")
    builder.button(text="6+ месяцев",     callback_data="onb:break:6plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_run_feel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="😮‍💨 Тяжело, задыхаюсь",   callback_data="onb:feel:hard")
    builder.button(text="😐 Нормально, но устаю",    callback_data="onb:feel:medium")
    builder.button(text="😊 Комфортно",              callback_data="onb:feel:easy")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет боли", callback_data="onb:pain:none")
    builder.button(text="Небольшая боль", callback_data="onb:pain:little")
    builder.button(text="Да, есть боль", callback_data="onb:pain:yes")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain_location(selected: list[str]) -> InlineKeyboardMarkup:
    options = [
        ("Колени",  "knees"),
        ("Стопы",   "feet"),
        ("Голень",  "shin"),
        ("Ахилл",   "achilles"),
        ("Спина",   "back"),
        ("Другое",  "other"),
    ]
    builder = InlineKeyboardBuilder()
    for label, value in options:
        prefix = "✅ " if value in selected else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"onb:pain_loc:{value}")
    builder.button(text="Готово →", callback_data="onb:pain_loc:done")
    builder.adjust(2)
    return builder.as_markup()


def kb_injury_history() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Нет", callback_data="onb:injury:no")
    builder.button(text="Да",  callback_data="onb:injury:yes")
    builder.adjust(2)
    return builder.as_markup()


def kb_other_sports(selected: list[str]) -> InlineKeyboardMarkup:
    options = [
        ("Зал",        "gym"),
        ("Велосипед",  "bike"),
        ("Плавание",   "swim"),
        ("Другое",     "other"),
    ]
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Нет, только бег" if "none" in selected else "Нет, только бег",
        callback_data="onb:sports:none",
    )
    for label, value in options:
        prefix = "✅ " if value in selected else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"onb:sports:{value}")
    builder.button(text="Готово →", callback_data="onb:sports:done")
    builder.adjust(2)
    return builder.as_markup()


def kb_strength_frequency() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Не делаю",  callback_data="onb:str_freq:no")
    builder.button(text="Иногда",    callback_data="onb:str_freq:sometimes")
    builder.button(text="Регулярно", callback_data="onb:str_freq:regularly")
    builder.adjust(1)
    return builder.as_markup()


def kb_self_level() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🐣 Новичок",    callback_data="onb:self_lvl:beginner")
    builder.button(text="📗 Базовый",    callback_data="onb:self_lvl:base")
    builder.button(text="📘 Средний",    callback_data="onb:self_lvl:medium")
    builder.button(text="📕 Продвинутый", callback_data="onb:self_lvl:advanced")
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


def kb_yesterday_completion() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнил(а)", callback_data="ci:yday:done")
    builder.button(text="⚡ Частично", callback_data="ci:yday:partial")
    builder.button(text="❌ Нет", callback_data="ci:yday:skipped")
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


def kb_completion_strength() -> InlineKeyboardMarkup:
    """Completion buttons + custom workout option for strength days."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнено", callback_data="wk:status:done")
    builder.button(text="⚡ Частично", callback_data="wk:status:partial")
    builder.button(text="❌ Пропустил(а)", callback_data="wk:status:skipped")
    builder.button(text="🔄 Сделаю свою тренировку", callback_data="wk:custom")
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
    builder.button(text="📢 Отправить чек-ин всем", callback_data="adm:broadcast:checkin")
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


def kb_admin_manage(user_id: int, extended: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Изменить режим дня", callback_data=f"adm:mode:{user_id}")
    builder.button(text="⏭️ Перейти к дню", callback_data=f"adm:jump:{user_id}")
    builder.button(text="🎯 Изменить уровень", callback_data=f"adm:pick:{user_id}")
    builder.button(text="📝 Отметить тренировку", callback_data=f"adm:markday:{user_id}")
    builder.button(text="✉️ Отправить сообщение", callback_data=f"adm:msg:{user_id}")
    if not extended:
        builder.button(text="➕ Продлить на 5-ю неделю", callback_data=f"adm:extend:{user_id}")
    else:
        builder.button(text="✅ 5-я неделя активна", callback_data=f"adm:extend:off:{user_id}")
    builder.button(text="◀️ Назад", callback_data=f"adm:report:view:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_mark_day_picker(user_id: int, logs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for log in logs:
        builder.button(
            text=f"День {log.day_index} ({log.date.strftime('%d.%m')})",
            callback_data=f"adm:markday:day:{user_id}:{log.day_index}",
        )
    builder.button(text="◀️ Назад", callback_data=f"adm:manage:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_mark_day_status(user_id: int, day_index: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнено", callback_data=f"adm:markday:set:{user_id}:{day_index}:done")
    builder.button(text="⚡ Частично", callback_data=f"adm:markday:set:{user_id}:{day_index}:partial")
    builder.button(text="❌ Пропущено", callback_data=f"adm:markday:set:{user_id}:{day_index}:skipped")
    builder.button(text="◀️ Назад", callback_data=f"adm:markday:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_checkin_approve(user_id: int) -> InlineKeyboardMarkup:
    """Sent to admin after user completes check-in — choose workout version."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💪 Base",     callback_data=f"adm:ca:{user_id}:base")
    builder.button(text="🔆 Light",    callback_data=f"adm:ca:{user_id}:light")
    builder.button(text="🔄 Recovery", callback_data=f"adm:ca:{user_id}:recovery")
    builder.button(text="😴 Отдых",    callback_data=f"adm:ca:{user_id}:rest")
    builder.adjust(2)
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
