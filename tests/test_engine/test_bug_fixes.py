"""
tests/test_engine/test_bug_fixes.py
Regression tests for specific bugs and new logic.
"""
from engine.week_planner import _count_run_days, split_running_minutes
from engine.level_assignment import detect_after_break_mode, OnboardingAnswers


def _answers(**kwargs) -> OnboardingAnswers:
    defaults = dict(
        runs=True, frequency="2_3", volume="10_25", structure=True,
        had_break=False, pain="none", pain_increases="no", location="gym",
        q_break_duration="no", q_longest_run="15_30",
        q_continuous_run_test="yes", q_goal="health",
    )
    defaults.update(kwargs)
    return OnboardingAnswers(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# Bug B regression: _count_run_days
# ══════════════════════════════════════════════════════════════════════════════

class TestCountRunDays:

    def test_l1_3_days(self):
        # 1 strength → min(3-1, 3) = 2
        assert _count_run_days(1, "base", False, 3) == 2

    def test_l1_4_days(self):
        # 1 strength → min(4-1, 3) = 3
        assert _count_run_days(1, "base", False, 4) == 3

    def test_l1_5_days(self):
        # 2 strength → min(5-2, 3) = 3
        assert _count_run_days(1, "base", False, 5) == 3

    def test_l1_6_days_capped_at_3(self):
        # 2 strength → min(6-2, 3) = 3 (capped)
        assert _count_run_days(1, "base", False, 6) == 3

    def test_l2_4_days(self):
        # 1 strength → min(4-1, 4) = 3
        assert _count_run_days(2, "base", False, 4) == 3

    def test_l2_5_days(self):
        # 2 strength → min(5-2, 4) = 3
        assert _count_run_days(2, "base", False, 5) == 3

    def test_l2_6_days(self):
        # 2 strength → min(6-2, 4) = 4
        assert _count_run_days(2, "base", False, 6) == 4

    def test_l3_return_4_days(self):
        # Like L2: 1 strength → min(4-1, 4) = 3
        assert _count_run_days(3, "base", True, 4) == 3

    def test_l3_return_5_days(self):
        # 2 strength → min(5-2, 4) = 3
        assert _count_run_days(3, "base", True, 5) == 3

    def test_l3_regular_4_days(self):
        # Always 2 strength → min(4-2, 5) = 2
        assert _count_run_days(3, "base", False, 4) == 2

    def test_l3_regular_5_days(self):
        # Always 2 strength → min(5-2, 5) = 3
        assert _count_run_days(3, "base", False, 5) == 3

    def test_l3_regular_7_days_capped_at_5(self):
        # Always 2 strength → min(7-2, 5) = 5 (capped)
        assert _count_run_days(3, "base", False, 7) == 5


# ══════════════════════════════════════════════════════════════════════════════
# Bug A regression: split_running_minutes at low L2 volume
# ══════════════════════════════════════════════════════════════════════════════

class TestSplitL2LowVolume:

    def _split(self, target: int, n_run: int = 4) -> dict:
        return split_running_minutes(
            weekly_target=target, level=2, period="base",
            injury_return=False, n_run_days=n_run,
            is_long_independent=False, is_recovery_week=False,
        )

    def test_150min_no_inverted_intensities(self):
        """Bug A: at 150 min / 4 run days, aerobic must not be < recovery_run."""
        m = self._split(150)
        assert m["recovery_run"] == 0 or m["aerobic"] >= m["recovery_run"], (
            f"Inverted: aerobic={m['aerobic']} < recovery_run={m['recovery_run']}"
        )

    def test_150min_long_can_be_below_50(self):
        """At L2 start, long < 50 min is explicitly acceptable per spec."""
        m = self._split(150)
        assert 0 < m["long"] <= 150

    def test_200min_recovery_run_present(self):
        """At normal L2 volume, recovery_run must be included."""
        m = self._split(200)
        assert m["recovery_run"] > 0

    def test_200min_aerobic_not_below_recovery(self):
        m = self._split(200)
        assert m["aerobic"] >= m["recovery_run"]

    def test_2_run_days_no_recovery_slot(self):
        """With only 2 run days (long + 1), no room for recovery_run."""
        m = self._split(120, n_run=2)
        assert m["recovery_run"] == 0

    def test_total_minutes_near_target(self):
        """Sum of per-day minutes times days should be close to weekly target."""
        n = 4
        m = self._split(150, n_run=n)
        n_other = n - 1
        if m["recovery_run"] > 0:
            total = m["long"] + m["recovery_run"] + m["aerobic"] * (n_other - 1)
        else:
            total = m["long"] + m["aerobic"] * n_other
        assert abs(total - 150) <= 5


# ══════════════════════════════════════════════════════════════════════════════
# detect_after_break_mode
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectAfterBreakMode:

    def test_level1_always_false(self):
        for dur in ("no", "to_1m", "1_3m", "3_6m", "6plus"):
            assert detect_after_break_mode(1, _answers(q_break_duration=dur)) is False

    def test_l2_no_break(self):
        assert detect_after_break_mode(2, _answers(q_break_duration="no")) is False

    def test_l2_short_break(self):
        assert detect_after_break_mode(2, _answers(q_break_duration="to_1m")) is False

    def test_l2_medium_break(self):
        assert detect_after_break_mode(2, _answers(q_break_duration="1_3m")) is False

    def test_l2_long_break_3_6m(self):
        assert detect_after_break_mode(2, _answers(q_break_duration="3_6m")) is True

    def test_l2_long_break_6plus(self):
        assert detect_after_break_mode(2, _answers(q_break_duration="6plus")) is True

    def test_l3_long_break(self):
        assert detect_after_break_mode(3, _answers(q_break_duration="3_6m")) is True

    def test_l3_short_break(self):
        assert detect_after_break_mode(3, _answers(q_break_duration="to_1m")) is False
