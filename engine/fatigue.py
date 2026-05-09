"""
engine/fatigue.py — DEPRECATED
Этот модуль удалён из новой логики (spec раздел 4.2.3).
Оставлен как заглушка для обратной совместимости со старыми 28-дневными пользователями.
Новый код НЕ должен импортировать отсюда.
"""
from __future__ import annotations
import warnings
from dataclasses import dataclass, field

FATIGUE_WINDOW = 3


@dataclass
class RecentLogData:
    """DEPRECATED. Используется только старой логикой для 28-дневных пользователей."""
    effort_level: int | None
    sleep_quality: int
    completion_status: str | None
    wellbeing: int = 2
    stress_level: int = 1
    day_type: str | None = None
    pain_level: int = 1


def _is_tough_day(log: RecentLogData) -> bool:
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
    """DEPRECATED."""
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    return sum(1 for log in window if _is_tough_day(log)) >= 2


def detect_severe_fatigue(recent_logs: list[RecentLogData]) -> bool:
    """DEPRECATED."""
    window = recent_logs[-FATIGUE_WINDOW:]
    return len(window) >= 3 and all(_is_tough_day(log) for log in window)


def detect_persistent_pain(recent_logs: list[RecentLogData]) -> bool:
    """DEPRECATED."""
    window = recent_logs[-FATIGUE_WINDOW:]
    if len(window) < 2:
        return False
    return sum(1 for log in window if log.pain_level >= 2) >= 2
