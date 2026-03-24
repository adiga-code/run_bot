from dataclasses import dataclass

from engine.red_flags import CheckinData, detect_red_flag
from engine.fatigue import RecentLogData


@dataclass
class WorkoutDecision:
    version: str           # base / light / recovery / rest
    reason: str            # human-readable reason (for logs/telemetry)
    red_flag: bool
    fatigue_reduction: bool


def _check_pain_two_days(recent_logs: list[RecentLogData]) -> bool:
    """Return True if the last 2 completed days both had pain (pain_level > 1).

    RecentLogData does not carry pain_level directly, but a wellbeing of 1
    combined with low effort is a reliable signal.  The simpler guard used here:
    if there are at least 2 recent logs and both had wellbeing <= 2 we treat it
    as a red-flag pattern and force recovery.
    """
    if len(recent_logs) >= 2:
        last_two = recent_logs[-2:]
        if all(log.wellbeing is not None and log.wellbeing <= 2 for log in last_two):
            return True
    return False


def decide_workout_version(
    checkin: CheckinData,
    recent_logs: list[RecentLogData],
    day_type: str,
    prev_day_type: str | None = None,
) -> WorkoutDecision:
    """
    Selects workout version using simple direct mapping.

    Priority chain:
      1. Rest day → always rest
      2. pain == 3 (есть) → recovery
      3. wellbeing == 1 (плохо) → recovery
      4. Red flag (pain escalates, etc.) → recovery
      5. Pain 2 days in a row (red flag pattern) → recovery
      6. pain == 2 (немного) → light
      7. wellbeing == 2 (тяжеловато) → light
      8. everything else → base
    """
    if day_type == "rest":
        return WorkoutDecision(
            version="rest",
            reason="день отдыха по плану",
            red_flag=False,
            fatigue_reduction=False,
        )

    # Priority 1: pain есть (3) → recovery
    if checkin.pain_level == 3:
        return WorkoutDecision(
            version="recovery",
            reason="боль: уровень 3 (есть)",
            red_flag=True,
            fatigue_reduction=False,
        )

    # Priority 2: wellbeing плохо (1) → recovery
    if checkin.wellbeing == 1:
        return WorkoutDecision(
            version="recovery",
            reason="самочувствие: плохо (1)",
            red_flag=False,
            fatigue_reduction=False,
        )

    # Red flag check (pain_increases, combined bad state, etc.)
    if detect_red_flag(checkin):
        return WorkoutDecision(
            version="recovery",
            reason="красный флаг: нарастающая боль",
            red_flag=True,
            fatigue_reduction=False,
        )

    # Pain 2 days in a row → recovery
    if _check_pain_two_days(recent_logs):
        return WorkoutDecision(
            version="recovery",
            reason="боль два дня подряд — восстановление",
            red_flag=False,
            fatigue_reduction=True,
        )

    # Priority 3: pain немного (2) → light
    if checkin.pain_level == 2:
        return WorkoutDecision(
            version="light",
            reason="боль: уровень 2 (немного)",
            red_flag=False,
            fatigue_reduction=False,
        )

    # Priority 4: wellbeing тяжеловато (2) → light
    if checkin.wellbeing == 2:
        return WorkoutDecision(
            version="light",
            reason="самочувствие: тяжеловато (2)",
            red_flag=False,
            fatigue_reduction=False,
        )

    # Everything else → base
    return WorkoutDecision(
        version="base",
        reason="хорошее самочувствие",
        red_flag=False,
        fatigue_reduction=False,
    )
