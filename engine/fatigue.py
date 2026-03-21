from dataclasses import dataclass

FATIGUE_MIN_TOUGH_DAYS = 2
FATIGUE_WINDOW = 3


@dataclass
class RecentLogData:
    effort_level: int | None       # 1-5 (5=max effort), None if skipped
    sleep_quality: int             # 1=плохо, 2=нормально, 3=хорошо
    completion_status: str | None  # done / partial / skipped
    wellbeing: int = 3             # 1=плохо, 2=тяжеловато, 3=нормально, 4=отлично
    stress_level: int = 1         # 1=нет, 2=умеренный, 3=сильный


def _is_tough_day(log: RecentLogData) -> bool:
    """
    A day counts as "tough" if ANY of:
    - High effort (≥4/5)
    - Poor sleep
    - Bad or heavy wellbeing (≤2)
    - Significant stress (≥2)
    - Workout was partial or skipped
    """
    if log.effort_level is not None and log.effort_level >= 4:
        return True
    if log.sleep_quality == 1:
        return True
    if log.wellbeing <= 2:
        return True
    if log.stress_level >= 2:
        return True
    if log.completion_status in ("partial", "skipped"):
        return True
    return False


def detect_cumulative_fatigue(recent_logs: list[RecentLogData]) -> bool:
    """
    Returns True if 2+ of the last FATIGUE_WINDOW days were "tough".
    Triggers automatic load reduction on the next day.
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    tough_days = sum(1 for log in window if _is_tough_day(log))
    return tough_days >= FATIGUE_MIN_TOUGH_DAYS
