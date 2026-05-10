"""
tests/test_engine/test_rule_engine.py

Тесты новой engine/rule_engine.py (spec раздел 3.7.1).
Приоритеты версии тренировки:
  1. day_type == "rest"                        → rest
  2. pain == 3                                 → recovery
  3. pain == 2                                 → light
  4. wellbeing == 1                            → light
  5. sleep == 1 ИЛИ stress == 3               → light
  6. вчера pain ≥ 2, сегодня pain == 1         → light
  7. иначе                                     → base
"""
import pytest
from engine.rule_engine import CheckinData, RecentDayData, WorkoutDecision, decide_workout_version


# ── Вспомогательные функции ───────────────────────────────────────────────────

def good() -> CheckinData:
    """Отличное состояние — нет триггеров."""
    return CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=1)


def ok() -> CheckinData:
    return CheckinData(wellbeing=2, sleep_quality=2, pain_level=1, stress_level=1)


def yesterday_ok() -> RecentDayData:
    return RecentDayData(pain_level=1)


def yesterday_pain2() -> RecentDayData:
    return RecentDayData(pain_level=2)


def yesterday_pain3() -> RecentDayData:
    return RecentDayData(pain_level=3)


# ══════════════════════════════════════════════════════════════════════════════
# 1. День отдыха — всегда rest
# ══════════════════════════════════════════════════════════════════════════════

def test_rest_day_is_always_rest():
    """day_type=rest → rest, независимо от состояния."""
    decision = decide_workout_version(
        CheckinData(wellbeing=1, sleep_quality=1, pain_level=3, stress_level=3),
        day_type="rest",
    )
    assert decision.version == "rest"


def test_rest_day_good_state_still_rest():
    decision = decide_workout_version(good(), day_type="rest")
    assert decision.version == "rest"


# ══════════════════════════════════════════════════════════════════════════════
# 2. pain == 3 → recovery (наивысший приоритет среди не-rest)
# ══════════════════════════════════════════════════════════════════════════════

def test_pain3_gives_recovery_run():
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=3, stress_level=1),
        day_type="run",
    )
    assert decision.version == "recovery"


def test_pain3_gives_recovery_strength():
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=3, stress_level=1),
        day_type="strength",
    )
    assert decision.version == "recovery"


def test_pain3_overrides_everything():
    """pain==3 имеет приоритет даже при хорошем самочувствии."""
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=3, stress_level=1),
        day_type="run",
        yesterday=yesterday_ok(),
    )
    assert decision.version == "recovery"


# ══════════════════════════════════════════════════════════════════════════════
# 3. pain == 2 → light
# ══════════════════════════════════════════════════════════════════════════════

def test_pain2_gives_light():
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=2, stress_level=1),
        day_type="run",
    )
    assert decision.version == "light"


def test_pain2_is_not_recovery():
    """pain==2 → light, НЕ recovery."""
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=2, stress_level=1),
        day_type="run",
    )
    assert decision.version != "recovery"


# ══════════════════════════════════════════════════════════════════════════════
# 4. wellbeing == 1 → light
# ══════════════════════════════════════════════════════════════════════════════

def test_wellbeing1_gives_light():
    decision = decide_workout_version(
        CheckinData(wellbeing=1, sleep_quality=3, pain_level=1, stress_level=1),
        day_type="run",
    )
    assert decision.version == "light"


def test_wellbeing2_no_other_triggers_gives_base():
    decision = decide_workout_version(
        CheckinData(wellbeing=2, sleep_quality=3, pain_level=1, stress_level=1),
        day_type="run",
    )
    assert decision.version == "base"


# ══════════════════════════════════════════════════════════════════════════════
# 5. sleep == 1 или stress == 3 → light
# ══════════════════════════════════════════════════════════════════════════════

def test_bad_sleep_gives_light():
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=1, pain_level=1, stress_level=1),
        day_type="run",
    )
    assert decision.version == "light"


def test_high_stress_gives_light():
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=3),
        day_type="run",
    )
    assert decision.version == "light"


def test_medium_stress_no_other_gives_base():
    """stress==2 без других триггеров → base."""
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=2),
        day_type="run",
    )
    assert decision.version == "base"


def test_medium_sleep_no_other_gives_base():
    """sleep==2 без других триггеров → base."""
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=2, pain_level=1, stress_level=1),
        day_type="run",
    )
    assert decision.version == "base"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Возврат после боли: вчера pain ≥ 2, сегодня pain == 1 → light
# ══════════════════════════════════════════════════════════════════════════════

def test_recovery_after_pain2_gives_light():
    """Вчера была боль 2, сегодня нет → 1 день light."""
    decision = decide_workout_version(
        good(),
        day_type="run",
        yesterday=yesterday_pain2(),
    )
    assert decision.version == "light"


def test_recovery_after_pain3_gives_light():
    """Вчера была боль 3 (прошла), сегодня pain=1 → light."""
    decision = decide_workout_version(
        good(),
        day_type="run",
        yesterday=yesterday_pain3(),
    )
    assert decision.version == "light"


def test_no_pain_yesterday_good_today_gives_base():
    """Вчера pain=1, сегодня хорошо → base."""
    decision = decide_workout_version(
        good(),
        day_type="run",
        yesterday=yesterday_ok(),
    )
    assert decision.version == "base"


def test_no_yesterday_good_gives_base():
    """Нет истории вчерашнего дня → base."""
    decision = decide_workout_version(good(), day_type="run", yesterday=None)
    assert decision.version == "base"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Всё нормально → base
# ══════════════════════════════════════════════════════════════════════════════

def test_good_state_gives_base():
    decision = decide_workout_version(good(), day_type="run")
    assert decision.version == "base"


def test_ok_state_strength_gives_base():
    decision = decide_workout_version(ok(), day_type="strength")
    assert decision.version == "base"


def test_recovery_day_type_good_state():
    """day_type=recovery + хорошее состояние → base (версия для recovery-тренировки)."""
    decision = decide_workout_version(good(), day_type="recovery")
    assert decision.version == "base"


# ══════════════════════════════════════════════════════════════════════════════
# Приоритет: боль перед самочувствием
# ══════════════════════════════════════════════════════════════════════════════

def test_pain2_overrides_good_wellbeing():
    """pain==2 важнее wellbeing==3."""
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=2, stress_level=1),
        day_type="run",
    )
    assert decision.version == "light"


def test_pain3_overrides_good_sleep_and_wellbeing():
    """pain==3 → recovery, даже если всё остальное хорошо."""
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=3, stress_level=1),
        day_type="run",
    )
    assert decision.version == "recovery"


# ══════════════════════════════════════════════════════════════════════════════
# Поле reason — должно быть непустым
# ══════════════════════════════════════════════════════════════════════════════

def test_decision_has_reason():
    decision = decide_workout_version(good(), day_type="run")
    assert decision.reason
    assert isinstance(decision.reason, str)


def test_recovery_decision_has_reason():
    decision = decide_workout_version(
        CheckinData(wellbeing=3, sleep_quality=3, pain_level=3, stress_level=1),
        day_type="run",
    )
    assert decision.reason
