"""
Pre-written check-in interpretation texts shown to the user after morning check-in.
All text lives in texts.py → T.interpretations.
"""

<<<<<<< HEAD
from texts import T
=======
# Maps WorkoutDecision.version + context → interpretation text
INTERPRETATIONS: dict[str, str] = {
    "red_flag": (
        "🛑 Сегодня лучше не бежать — это защита от травмы. "
        "Тело просит восстановления, и мы его слушаем.\n\n"
        "Восстановление сегодня — это и есть твоя тренировка. "
        "Ты следуешь системе, и это правильно 💪"
    ),
    "fatigue_recovery": (
        "😴 Видно накопилась усталость за последние дни. "
        "Снизим нагрузку — восстановление тоже часть тренировки.\n\n"
        "Восстановление сегодня — это и есть твоя тренировка. "
        "Ты следуешь системе, и это правильно 💪"
    ),
    "fatigue_light": (
        "😴 Видно накопилась усталость. "
        "Сегодня лёгкий вариант — тело получит нагрузку без лишнего стресса."
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
>>>>>>> 9d10903f55c61134f71c6a8dd1e9afb5f0cd3e89


def get_interpretation(version: str, checkin_wellbeing: int, red_flag: bool, fatigue_reduction: bool) -> str:
    """Return the right interpretation text based on rule engine output."""
    if version == "rest":
        return T.interpretations.rest
    if red_flag:
        return T.interpretations.red_flag
    if fatigue_reduction:
<<<<<<< HEAD
        return T.interpretations.fatigue
=======
        if version == "recovery":
            return INTERPRETATIONS["fatigue_recovery"]
        return INTERPRETATIONS["fatigue_light"]
>>>>>>> 9d10903f55c61134f71c6a8dd1e9afb5f0cd3e89
    if version == "recovery":
        return T.interpretations.red_flag  # recovery without explicit red flag → same message
    if version == "light":
<<<<<<< HEAD
        return T.interpretations.light_wellbeing
=======
        return INTERPRETATIONS["light_wellbeing"]
>>>>>>> 9d10903f55c61134f71c6a8dd1e9afb5f0cd3e89
    # base
    if checkin_wellbeing >= 4:
        return T.interpretations.base_great
    return T.interpretations.base_ok
