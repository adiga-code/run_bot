"""
Pre-written check-in interpretation texts shown to the user after morning check-in.
Keyed by rule engine decision reason category.
"""

# Maps WorkoutDecision.version + context → interpretation text
INTERPRETATIONS: dict[str, str] = {
    "red_flag": (
        "🛑 Есть сигналы, что тело сейчас не готово к нагрузке.\n"
        "Сегодня — восстановление. Это правильное решение 💪"
    ),
    "fatigue_recovery": (
        "😴 Накопилась усталость за несколько дней.\n"
        "Сегодня вместо тренировки — восстановление. Это тоже работа."
    ),
    "fatigue_light": (
        "😴 Чувствуется накопленная усталость.\n"
        "Сегодня лёгкий вариант тренировки — двигаемся, но без лишней нагрузки."
    ),
    "light_wellbeing": (
        "😐 Самочувствие не на высоте.\n"
        "Сегодня лёгкий вариант тренировки — двигаемся, но без усилия."
    ),
    "light_sleep": (
        "😴 Плохой сон — уже нагрузка на тело.\n"
        "Сегодня лёгкий вариант, чтобы не перегрузить."
    ),
    "light_pain": (
        "⚠️ Есть боль — снижаем нагрузку.\n"
        "Сегодня лёгкий вариант тренировки."
    ),
    "base_ok": (
        "✅ Всё в порядке. Идём по плану."
    ),
    "base_great": (
        "💪 Отличное состояние! Полная тренировка по плану."
    ),
    "rest": (
        "🌿 Сегодня день отдыха.\n"
        "Отдых — часть тренировочного процесса."
    ),
}


def get_interpretation(version: str, checkin_wellbeing: int, red_flag: bool, fatigue_reduction: bool) -> str:
    """Return the right interpretation text based on rule engine output."""
    if version == "rest":
        return INTERPRETATIONS["rest"]
    if red_flag:
        return INTERPRETATIONS["red_flag"]
    if fatigue_reduction:
        if version == "recovery":
            return INTERPRETATIONS["fatigue_recovery"]
        return INTERPRETATIONS["fatigue_light"]
    if version == "recovery":
        return INTERPRETATIONS["red_flag"]  # recovery without explicit red flag → same message
    if version == "light":
        return INTERPRETATIONS["light_wellbeing"]
    # base
    if checkin_wellbeing >= 4:
        return INTERPRETATIONS["base_great"]
    return INTERPRETATIONS["base_ok"]
