from dataclasses import dataclass

FATIGUE_WINDOW = 3


@dataclass
class RecentLogData:
    effort_level: int | None       # 1-5 (5=max effort), None if skipped
    sleep_quality: int             # 1=плохо, 2=средне, 3=хорошо
    completion_status: str | None  # done / partial / skipped
    wellbeing: int = 2             # 1=плохо, 2=нормально, 3=отлично
    stress_level: int = 1          # 1=низкий, 2=средний, 3=высокий
    day_type: str | None = None    # run / strength / recovery / rest
    pain_level: int = 1            # 1=нет, 2=немного, 3=есть


def _is_tough_day(log: RecentLogData) -> bool:
    """
    День считается «тяжёлым» если:
    - самочувствие плохо (1)
    - стресс средний или высокий (>= 2)
    - сон плохой (1)
    - высокое усилие (>= 4)
    - тренировка выполнена частично или пропущена
    - есть какая-либо боль (>= 2)
    """
    if log.wellbeing == 1:
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
    Возвращает True если 2+ из последних 3 дней были «тяжёлыми».
    Триггер для снижения нагрузки (base → light).
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    tough_days = sum(1 for log in window if _is_tough_day(log))
    return tough_days >= 2


def detect_severe_fatigue(recent_logs: list[RecentLogData]) -> bool:
    """
    Возвращает True если ВСЕ 3 последних дня были «тяжёлыми».
    Триггер для принудительного дня восстановления.
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    return len(window) >= 3 and all(_is_tough_day(log) for log in window)


def detect_persistent_pain(recent_logs: list[RecentLogData]) -> bool:
    """
    Возвращает True если боль >= 2 была 2 или более дней из последних 3.
    Красный флаг: боль «немного» 2 дня подряд → Recovery.
    """
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    pain_days = sum(1 for log in window if log.pain_level >= 2)
    return pain_days >= 2
