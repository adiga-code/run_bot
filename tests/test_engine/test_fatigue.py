import pytest
from engine.fatigue import RecentLogData, detect_cumulative_fatigue


def log(
    effort: int | None = 2,
    sleep: int = 2,
    status: str = "done",
    wellbeing: int = 3,
    stress: int = 1,
) -> RecentLogData:
    return RecentLogData(
        effort_level=effort,
        sleep_quality=sleep,
        completion_status=status,
        wellbeing=wellbeing,
        stress_level=stress,
    )


# ── Fatigue detected ──────────────────────────────────────────────────────────

def test_fatigue_two_high_effort_days():
    logs = [log(effort=4), log(effort=5), log(effort=2)]
    assert detect_cumulative_fatigue(logs) is True


def test_fatigue_two_bad_sleep_days():
    logs = [log(sleep=1), log(sleep=1), log(effort=2)]
    assert detect_cumulative_fatigue(logs) is True


def test_fatigue_mixed_effort_and_sleep():
    logs = [log(effort=4), log(sleep=1)]
    assert detect_cumulative_fatigue(logs) is True


def test_fatigue_three_tough_days():
    logs = [log(effort=5), log(effort=4), log(sleep=1)]
    assert detect_cumulative_fatigue(logs) is True


def test_fatigue_only_last_3_days_counted():
    """Old history beyond the window should not contribute."""
    logs = [log(effort=5), log(effort=5), log(effort=5), log(effort=1), log(sleep=3)]
    # Window = last 3: effort=5, effort=1, sleep=3 → only 1 tough day → no fatigue
    assert detect_cumulative_fatigue(logs) is False


# ── No fatigue ────────────────────────────────────────────────────────────────

def test_no_fatigue_one_tough_day():
    logs = [log(effort=5), log(effort=1), log(sleep=3)]
    assert detect_cumulative_fatigue(logs) is False


def test_no_fatigue_all_easy():
    logs = [log(effort=2), log(effort=1), log(sleep=2)]
    assert detect_cumulative_fatigue(logs) is False


def test_fatigue_skipped_days_are_tough():
    """Skipped days count as tough (completion_status='skipped')."""
    logs = [log(effort=None, status="skipped"), log(effort=None, status="skipped")]
    assert detect_cumulative_fatigue(logs) is True


def test_no_fatigue_one_skipped_day():
    """A single skipped day is not enough for fatigue detection."""
    logs = [log(effort=None, status="skipped"), log(effort=2, status="done")]
    assert detect_cumulative_fatigue(logs) is False


def test_no_fatigue_insufficient_history():
    """Less than 2 days → never report fatigue."""
    logs = [log(effort=5)]
    assert detect_cumulative_fatigue(logs) is False


def test_no_fatigue_empty_history():
    assert detect_cumulative_fatigue([]) is False


def test_fatigue_bad_wellbeing_days():
    """wellbeing ≤ 2 counts as tough."""
    logs = [log(wellbeing=1), log(wellbeing=2), log()]
    assert detect_cumulative_fatigue(logs) is True


def test_fatigue_high_stress_days():
    """stress ≥ 2 counts as tough."""
    logs = [log(stress=2), log(stress=3), log()]
    assert detect_cumulative_fatigue(logs) is True


def test_fatigue_partial_completion():
    """partial or skipped completion counts as tough."""
    logs = [log(status="partial"), log(status="skipped"), log()]
    assert detect_cumulative_fatigue(logs) is True
