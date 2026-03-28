from dataclasses import dataclass

FATIGUE_WINDOW = 3


@dataclass
class RecentLogData:
    effort_level: int | None       # 1-5 (5=max effort), None if skipped
    sleep_quality: int             # 1=плохо, 2=нормально, 3=хорошо
    completion_status: str | None  # done / partial / skipped
    wellbeing: int = 3             # 1=плохо, 2=тяжеловато, 3=нормально, 4=хорошо, 5=отлично
    stress_level: int = 1          # 1=нет, 2=умеренный, 3=сильный
    day_type: str | None = None    # run / strength / recovery / rest
    pain_level: int = 1            # 1=нет, 2=немного, 3=есть


def _is_tough_day(log: RecentLogData) -> bool:
    """
    A day is "tough" if wellbeing ≤ 2 (тяжеловато/плохо),
    or stress >= 2, or sleep is bad, or high effort, or workout was partial/skipped,
    or any pain reported.
    """
    if log.wellbeing <= 2:
        return True
    if log.stress_level >= 2:
        return True
    if log.sleep_quality == 1:
        return True
    if log.effort_level is not None and log.effort_level >= 4:
        return True
    if log.completion_status in ("partial", "skipped"):
        return True
    if log.pain_level >= 2:
        return True
    return False


def detect_cumulative_fatigue(recent_logs: list[RecentLogData]) -> bool:
    """
    Returns True if 2+ of the last 3 days were "tough".
    Triggers automatic load reduction (base → light).
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    tough_days = sum(1 for log in window if _is_tough_day(log))
    return tough_days >= 2


def detect_severe_fatigue(recent_logs: list[RecentLogData]) -> bool:
    """
    Returns True if ALL 3 of the last 3 days were "tough".
    Triggers forced recovery day.
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    return len(window) >= 3 and all(_is_tough_day(log) for log in window)


def detect_persistent_pain(recent_logs: list[RecentLogData]) -> bool:
    """
    Returns True if pain_level >= 2 was reported on 2 or more of the last 3 days.
    Persistent pain is a safety signal that should override Light and force Recovery.
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    pain_days = sum(1 for log in window if log.pain_level >= 2)
    return pain_days >= 2
