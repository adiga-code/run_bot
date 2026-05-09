"""
engine/rule_engine.py
Выбор версии тренировки по результатам чек-ина.
Новая логика (spec раздел 3.7.1) — упрощённый приоритет без fatigue-детектора.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckinData:
    """Данные утреннего чек-ина."""
    wellbeing: int       # 1=плохо, 2=тяжеловато, 3=нормально, 4=отлично
    sleep_quality: int   # 1=плохо, 2=средне, 3=хорошо
    pain_level: int      # 1=нет (0-2/10), 2=немного (3-5/10), 3=есть (6-10/10)
    stress_level: int    # 1=низкий, 2=средний, 3=высокий


@dataclass
class RecentDayData:
    """Минимальный слепок предыдущего дня для rule_engine."""
    pain_level: int      # 1/2/3, None-безопасно не нужен — передаём 1 если нет данных


@dataclass
class WorkoutDecision:
    version: str   # base / light / recovery / rest
    reason: str    # human-readable (для логов / телеметрии)


def decide_workout_version(
    checkin: CheckinData,
    day_type: str,
    yesterday: RecentDayData | None = None,
) -> WorkoutDecision:
    """
    Выбор версии тренировки по приоритету (раздел 3.7.1 spec):

    1. day_type == "rest"                        → Rest
    2. pain == 3 (есть)                          → Recovery
    3. pain == 2 (немного)                       → Light
    4. wellbeing == 1 (плохо)                    → Light
    5. sleep == 1 ИЛИ stress == 3               → Light
    6. Возврат после боли:
       вчера pain ≥ 2, сегодня pain == 1         → Light (1 день)
    7. Иначе                                     → Base
    """
    # ── 1. День отдыха ───────────────────────────────────────────────────────
    if day_type == "rest":
        return WorkoutDecision(version="rest", reason="день отдыха по плану")

    # ── 2. Боль «есть» ───────────────────────────────────────────────────────
    if checkin.pain_level == 3:
        return WorkoutDecision(version="recovery", reason="боль: есть (6–10/10)")

    # ── 3. Боль «немного» ────────────────────────────────────────────────────
    if checkin.pain_level == 2:
        return WorkoutDecision(version="light", reason="боль: немного (3–5/10)")

    # ── 4. Самочувствие плохо ────────────────────────────────────────────────
    if checkin.wellbeing == 1:
        return WorkoutDecision(version="light", reason="самочувствие: плохо")

    # ── 5. Плохой сон или высокий стресс ─────────────────────────────────────
    if checkin.sleep_quality == 1 or checkin.stress_level == 3:
        return WorkoutDecision(
            version="light",
            reason="плохой сон или высокий стресс",
        )

    # ── 6. Возврат после боли ────────────────────────────────────────────────
    if yesterday is not None and yesterday.pain_level >= 2 and checkin.pain_level == 1:
        return WorkoutDecision(
            version="light",
            reason="восстановление после боли — 1 день light",
        )

    # ── 7. Всё нормально ─────────────────────────────────────────────────────
    return WorkoutDecision(version="base", reason="хорошее самочувствие")
