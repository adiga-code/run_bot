import pytest
from engine.red_flags import CheckinData, detect_red_flag


def make_checkin(**overrides) -> CheckinData:
    """Base: отличное состояние — без красных флагов."""
    defaults = dict(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=1)
    defaults.update(overrides)
    return CheckinData(**defaults)


# ── Red flag cases ────────────────────────────────────────────────────────────

def test_red_flag_pain3():
    """Активная боль (уровень 3, есть 6-10) → красный флаг."""
    checkin = make_checkin(pain_level=3)
    assert detect_red_flag(checkin) is True


def test_red_flag_pain3_with_bad_wellbeing():
    checkin = make_checkin(wellbeing=1, pain_level=3)
    assert detect_red_flag(checkin) is True


def test_red_flag_bad_wellbeing_and_high_stress():
    """wellbeing=плохо(1) И стресс=высокий(3) → красный флаг."""
    checkin = make_checkin(wellbeing=1, pain_level=1, stress_level=3)
    assert detect_red_flag(checkin) is True


# ── Non-red-flag cases ────────────────────────────────────────────────────────

def test_no_red_flag_great_state():
    checkin = make_checkin()
    assert detect_red_flag(checkin) is False


def test_no_red_flag_pain2_alone():
    """Боль «немного» (уровень 2) — не красный флаг, только Light."""
    checkin = make_checkin(pain_level=2)
    assert detect_red_flag(checkin) is False


def test_no_red_flag_bad_wellbeing_no_stress():
    """Плохое самочувствие без высокого стресса — не красный флаг."""
    checkin = make_checkin(wellbeing=1, pain_level=1, stress_level=1)
    assert detect_red_flag(checkin) is False


def test_no_red_flag_bad_wellbeing_medium_stress():
    """wellbeing=1 + стресс средний (2, не высокий 3) — не красный флаг."""
    checkin = make_checkin(wellbeing=1, pain_level=1, stress_level=2)
    assert detect_red_flag(checkin) is False


def test_no_red_flag_bad_sleep_only():
    """Плохой сон — не красный флаг (только Light через rule_engine)."""
    checkin = make_checkin(wellbeing=3, sleep_quality=1, pain_level=1, stress_level=1)
    assert detect_red_flag(checkin) is False
