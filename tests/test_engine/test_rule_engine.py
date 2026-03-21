import pytest
from engine.red_flags import CheckinData
from engine.fatigue import RecentLogData
from engine.rule_engine import decide_workout_version


def good_checkin() -> CheckinData:
    return CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, pain_increases=None, stress_level=1)


def bad_checkin() -> CheckinData:
    # pain_level=3 → red flag regardless of wellbeing
    return CheckinData(wellbeing=1, sleep_quality=1, pain_level=3, pain_increases=None, stress_level=1)


def escalating_pain_checkin() -> CheckinData:
    return CheckinData(wellbeing=2, sleep_quality=2, pain_level=2, pain_increases=True, stress_level=1)


def ok_checkin() -> CheckinData:
    return CheckinData(wellbeing=2, sleep_quality=2, pain_level=1, pain_increases=None, stress_level=1)


def easy_logs(n: int = 3) -> list[RecentLogData]:
    return [RecentLogData(effort_level=2, sleep_quality=3, completion_status="done") for _ in range(n)]


def tough_logs(n: int = 3) -> list[RecentLogData]:
    return [RecentLogData(effort_level=5, sleep_quality=1, completion_status="done") for _ in range(n)]


# ── Rest day ──────────────────────────────────────────────────────────────────

def test_rest_day_always_rest():
    decision = decide_workout_version(bad_checkin(), tough_logs(), day_type="rest")
    assert decision.version == "rest"
    assert decision.red_flag is False


# ── Red flag → recovery ───────────────────────────────────────────────────────

def test_red_flag_gives_recovery():
    decision = decide_workout_version(bad_checkin(), easy_logs(), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True
    assert decision.fatigue_reduction is False


def test_escalating_pain_gives_recovery():
    decision = decide_workout_version(escalating_pain_checkin(), easy_logs(), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True


def test_red_flag_overrides_fatigue():
    """Red flag has higher priority than cumulative fatigue."""
    decision = decide_workout_version(bad_checkin(), tough_logs(), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True


# ── Cumulative fatigue → light ────────────────────────────────────────────────

def test_fatigue_gives_light():
    decision = decide_workout_version(good_checkin(), tough_logs(), day_type="run")
    assert decision.version == "light"
    assert decision.fatigue_reduction is True
    assert decision.red_flag is False


def test_fatigue_on_strength_day():
    decision = decide_workout_version(good_checkin(), tough_logs(), day_type="strength")
    assert decision.version == "light"


# ── Mild indicators → light ───────────────────────────────────────────────────

def test_bad_wellbeing_alone_gives_light():
    # wellbeing=1 → score +2 → light
    checkin = CheckinData(wellbeing=1, sleep_quality=3, pain_level=1, pain_increases=None, stress_level=1)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"
    assert decision.red_flag is False
    assert decision.fatigue_reduction is False


def test_bad_sleep_alone_gives_base():
    # sleep=1 → score +1 → base (score ≤ 1)
    checkin = CheckinData(wellbeing=3, sleep_quality=1, pain_level=1, pain_increases=None, stress_level=1)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "base"


def test_bad_sleep_and_moderate_stress_gives_light():
    # sleep=1 → +1, stress=2 → +1, total=2 → light
    checkin = CheckinData(wellbeing=3, sleep_quality=1, pain_level=1, pain_increases=None, stress_level=2)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"


def test_little_pain_gives_light():
    # wellbeing=2 → +1, pain=2 → +2, total=3 → light
    checkin = CheckinData(wellbeing=2, sleep_quality=2, pain_level=2, pain_increases=False, stress_level=1)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"


def test_high_stress_alone_gives_light():
    # stress=3 → +2 → light
    checkin = CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, pain_increases=None, stress_level=3)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"


# ── Good state → base ─────────────────────────────────────────────────────────

def test_good_state_gives_base():
    decision = decide_workout_version(good_checkin(), easy_logs(), day_type="run")
    assert decision.version == "base"
    assert decision.red_flag is False
    assert decision.fatigue_reduction is False


def test_ok_state_gives_base():
    decision = decide_workout_version(ok_checkin(), easy_logs(), day_type="strength")
    assert decision.version == "base"


# ── Recovery day_type ─────────────────────────────────────────────────────────

def test_recovery_day_type_with_good_state():
    """Recovery day_type with good state → base version of recovery workout."""
    decision = decide_workout_version(good_checkin(), easy_logs(), day_type="recovery")
    assert decision.version == "base"


# ── After-strength constraint ─────────────────────────────────────────────────

def test_after_strength_day_caps_at_light():
    """Good state after a strength day → at least light (not base)."""
    decision = decide_workout_version(
        good_checkin(), easy_logs(), day_type="run", prev_day_type="strength"
    )
    assert decision.version == "light"


def test_after_strength_bad_state_can_give_recovery():
    """After-strength only sets floor at light; bad state can still give recovery."""
    checkin = CheckinData(wellbeing=1, sleep_quality=1, pain_level=1, pain_increases=None, stress_level=3)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run", prev_day_type="strength")
    assert decision.version == "recovery"
