"""
Pre-written check-in interpretation texts shown to the user after morning check-in.
Keyed by rule engine decision reason category.
"""

# Maps WorkoutDecision.version + context → interpretation text
INTERPRETATIONS: dict[str, str] = {
    "red_flag": (
        "🛑 Сегодня лучше не бежать — это защита от травмы. "
        "Тело просит восстановления, и мы его слушаем."
    ),
    "fatigue": (
        "😴 Видно накопилась усталость за последние дни. "
        "Снизим нагрузку — восстановление тоже часть тренировки."
    ),
    "light_wellbeing": (
        "😐 Самочувствие пониженное. Выйдем чуть легче — "
        "так тело получит стимул без лишнего стресса."
    ),
    "light_sleep": (
        "😴 Плохой сон влияет на восстановление. "
        "Сегодня облегчённый вариант — тело скажет спасибо."
    ),
    "light_pain": (
        "⚠️ Небольшая боль — сигнал снизить нагрузку. "
        "Выполним лёгкий вариант и понаблюдаем."
    ),
    "base_ok": (
        "✅ Неплохое состояние. Идём по стандартному плану — слушаем тело в процессе."
    ),
    "base_great": (
        "💪 Отличное состояние! Готов к полноценной тренировке по плану."
    ),
    "rest": (
        "🌿 Сегодня день отдыха. Позволь телу восстановиться — "
        "это такая же часть программы, как и тренировки."
    ),
}


def get_interpretation(version: str, checkin_wellbeing: int, red_flag: bool, fatigue_reduction: bool) -> str:
    """Return the right interpretation text based on rule engine output."""
    if version == "rest":
        return INTERPRETATIONS["rest"]
    if red_flag:
        return INTERPRETATIONS["red_flag"]
    if fatigue_reduction:
        return INTERPRETATIONS["fatigue"]
    if version == "recovery":
        return INTERPRETATIONS["red_flag"]  # recovery without explicit red flag → same message
    if version == "light":
        # Pick most relevant light reason
        return INTERPRETATIONS["light_wellbeing"]
    # base
    if checkin_wellbeing == 3:
        return INTERPRETATIONS["base_great"]
    return INTERPRETATIONS["base_ok"]
