import pytest
from engine.red_flags import CheckinData, detect_red_flag


def make_checkin(**overrides) -> CheckinData:
    """Base: great state — no red flag."""
    defaults = dict(wellbeing=3, sleep_quality=3, pain_level=1, pain_increases=None, stress_level=1)
    defaults.update(overrides)
    return CheckinData(**defaults)


# ── Red flag cases ────────────────────────────────────────────────────────────

def test_red_flag_pain3():
    """Active pain (level 3) always triggers, regardless of wellbeing."""
    checkin = make_checkin(pain_level=3)
    assert detect_red_flag(checkin) is True


def test_red_flag_pain3_with_bad_wellbeing():
    checkin = make_checkin(wellbeing=1, pain_level=3)
    assert detect_red_flag(checkin) is True


def test_red_flag_pain_increases():
    checkin = make_checkin(pain_level=2, pain_increases=True)
    assert detect_red_flag(checkin) is True


def test_red_flag_pain_increases_regardless_of_wellbeing():
    """Escalating pain is always a red flag, even if wellbeing is fine."""
    checkin = make_checkin(wellbeing=3, sleep_quality=3, pain_level=2, pain_increases=True)
    assert detect_red_flag(checkin) is True


def test_red_flag_bad_wellbeing_and_high_stress():
    """wellbeing==1 AND stress==3 triggers, even without pain."""
    checkin = make_checkin(wellbeing=1, pain_level=1, stress_level=3)
    assert detect_red_flag(checkin) is True


# ── Non-red-flag cases ────────────────────────────────────────────────────────

def test_no_red_flag_great_state():
    checkin = make_checkin()
    assert detect_red_flag(checkin) is False


def test_no_red_flag_bad_wellbeing_no_pain_no_stress():
    """Bad wellbeing alone (without high stress) is not a red flag."""
    checkin = make_checkin(wellbeing=1, pain_level=1, stress_level=1)
    assert detect_red_flag(checkin) is False


def test_no_red_flag_bad_wellbeing_moderate_stress():
    """wellbeing==1 + moderate stress (not 3) is not a red flag."""
    checkin = make_checkin(wellbeing=1, pain_level=1, stress_level=2)
    assert detect_red_flag(checkin) is False


def test_no_red_flag_pain_not_increasing():
    checkin = make_checkin(pain_level=2, pain_increases=False)
    assert detect_red_flag(checkin) is False


def test_no_red_flag_pain_not_sure():
    """not_sure about pain increases → not a red flag by itself."""
    checkin = make_checkin(pain_level=2, pain_increases=None)
    assert detect_red_flag(checkin) is False
