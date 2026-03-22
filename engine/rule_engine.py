from dataclasses import dataclass

from engine.red_flags import CheckinData, detect_red_flag
from engine.fatigue import RecentLogData, detect_cumulative_fatigue, detect_severe_fatigue


@dataclass
class WorkoutDecision:
    version: str           # base / light / recovery / rest
    reason: str            # human-readable reason (for logs/telemetry)
    red_flag: bool
    fatigue_reduction: bool


def decide_workout_version(
    checkin: CheckinData,
    recent_logs: list[RecentLogData],
    day_type: str,
    prev_day_type: str | None = None,
) -> WorkoutDecision:
    """
    Selects workout version using direct mapping from client spec.

    Priority chain:
      1. Rest day → always rest
      2. Red flag → recovery
      3. Severe fatigue (3 tough days) → recovery
      4. Direct mapping: wellbeing/sleep/pain → base/light/recovery
      5. Cumulative fatigue (2 tough days) → base → light
      6. After-strength constraint → base → light
    """
    if day_type == "rest":
        return WorkoutDecision(
            version="rest",
            reason="день отдыха по плану",
            red_flag=False,
            fatigue_reduction=False,
        )

    if detect_red_flag(checkin):
        return WorkoutDecision(
            version="recovery",
            reason="красный флаг: активная боль или нарастающая боль",
            red_flag=True,
            fatigue_reduction=False,
        )

    severe = detect_severe_fatigue(recent_logs)
    if severe:
        return WorkoutDecision(
            version="recovery",
            reason="3 тяжёлых дня подряд — принудительное восстановление",
            red_flag=False,
            fatigue_reduction=True,
        )

    # Direct mapping (spec priority: recovery > light > base)
    # Recovery: wellbeing плохо(1) OR pain есть(3)
    if checkin.wellbeing == 1 or checkin.pain_level == 3:
        version = "recovery"
        reason = "плохое самочувствие или боль"
    # Light: wellbeing тяжеловато(2) OR sleep плохо(1) OR pain немного(2)
    elif checkin.wellbeing == 2 or checkin.sleep_quality == 1 or checkin.pain_level == 2:
        version = "light"
        reason = "умеренный дискомфорт"
    else:
        version = "base"
        reason = "хорошее самочувствие"

    fatigue = detect_cumulative_fatigue(recent_logs)
    after_strength = (prev_day_type == "strength" and day_type == "run")

    if version == "base":
        if fatigue:
            version = "light"
            reason = "накопленная усталость (2+ тяжёлых дня)"
        elif after_strength:
            version = "light"
            reason = "день после силовой"

    return WorkoutDecision(
        version=version,
        reason=reason,
        red_flag=False,
        fatigue_reduction=fatigue or severe,
    )
