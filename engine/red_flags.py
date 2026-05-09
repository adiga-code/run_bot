"""
engine/red_flags.py
Детектор красных флагов и серий боли.
Новая логика (spec раздел 3.11).

NULL (нет чек-ина за день) сбрасывает streak-счётчики.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DayPainData:
    """Минимальный слепок дня для расчёта pain-streak."""
    pain_level: int | None   # 1/2/3 или None (нет чек-ина)


def detect_high_pain_streak(recent_days: list[DayPainData], days: int = 3) -> bool:
    """
    Возвращает True если последние `days` дней подряд имеют pain == 3.
    NULL (нет чек-ина) сбрасывает счётчик — False.

    Используется для активации red_flag_active.
    """
    if len(recent_days) < days:
        return False

    window = recent_days[-days:]
    for day in window:
        if day.pain_level is None:
            return False          # пропуск сбрасывает серию
        if day.pain_level != 3:
            return False
    return True


def detect_mild_pain_streak(recent_days: list[DayPainData], days: int = 3) -> bool:
    """
    Возвращает True если последние `days` дней подряд имеют pain == 2.
    NULL сбрасывает счётчик — False.

    Используется для блокировки роста (не откат).
    """
    if len(recent_days) < days:
        return False

    window = recent_days[-days:]
    for day in window:
        if day.pain_level is None:
            return False
        if day.pain_level != 2:
            return False
    return True


def count_high_pain_streak(recent_days: list[DayPainData]) -> int:
    """
    Считает текущую непрерывную серию дней с pain==3 (с конца списка).
    Останавливается на первом дне без pain==3 или без чек-ина.
    """
    streak = 0
    for day in reversed(recent_days):
        if day.pain_level is None or day.pain_level != 3:
            break
        streak += 1
    return streak


def count_mild_pain_streak(recent_days: list[DayPainData]) -> int:
    """
    Считает текущую непрерывную серию дней с pain==2 (с конца списка).
    """
    streak = 0
    for day in reversed(recent_days):
        if day.pain_level is None or day.pain_level != 2:
            break
        streak += 1
    return streak
