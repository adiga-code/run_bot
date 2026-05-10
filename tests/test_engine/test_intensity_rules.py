"""
tests/test_engine/test_intensity_rules.py

Тесты условий добавления интенсивных тренировок (spec раздел 3.10).
  - L1 base_in: никогда
  - L1 base: не ранее 8-й недели программы
  - L2 base: после 3 успешных недель подряд
  - Боль в последние 2 нед блокирует
  - Средн. Light > 2/нед за 4 нед блокирует
  - Средн. Recovery > 1/нед за 4 нед блокирует
  - recovery_period: никогда
  - MAX_INTENSITY_PER_WEEK проверяем константы
"""
import pytest
from engine.week_planner import can_add_intensity, WeekStats
from engine.constants import MAX_INTENSITY_PER_WEEK, MAX_INTERVALS_PER_WEEK


def good_weeks(n: int = 4) -> list[WeekStats]:
    return [
        WeekStats(growth_eligible=True, light_days=0, recovery_days=0, had_high_pain=False)
        for _ in range(n)
    ]


def weeks_with_pain(pain_at: int = -1) -> list[WeekStats]:
    """4 недели, одна (по умолчанию последняя) с болью."""
    weeks = good_weeks(4)
    idx = pain_at if pain_at >= 0 else len(weeks) + pain_at
    weeks[idx] = WeekStats(
        growth_eligible=False, light_days=0, recovery_days=0, had_high_pain=True
    )
    return weeks


def weeks_with_light(light_per_week: int = 3) -> list[WeekStats]:
    return [
        WeekStats(growth_eligible=True, light_days=light_per_week, recovery_days=0, had_high_pain=False)
        for _ in range(4)
    ]


def weeks_with_recovery(rec_per_week: int = 2) -> list[WeekStats]:
    return [
        WeekStats(growth_eligible=True, light_days=0, recovery_days=rec_per_week, had_high_pain=False)
        for _ in range(4)
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Запрещённые периоды / уровни
# ══════════════════════════════════════════════════════════════════════════════

class TestIntensityForbidden:

    def test_l1_base_in_never(self):
        ok = can_add_intensity(
            level=1, period="base_in", injury_return=False,
            program_week_number=20, growth_streak=10,
            recent_weeks=good_weeks(8),
        )
        assert ok is False

    def test_l1_recovery_period_never(self):
        ok = can_add_intensity(
            level=1, period="recovery_period", injury_return=False,
            program_week_number=20, growth_streak=0,
            recent_weeks=good_weeks(4),
        )
        assert ok is False

    def test_l3_recovery_period_never(self):
        ok = can_add_intensity(
            level=3, period="recovery_period", injury_return=False,
            program_week_number=20, growth_streak=5,
            recent_weeks=good_weeks(4),
        )
        assert ok is False

    def test_no_history_never(self):
        """Нет истории недель → нельзя добавить интенсивность."""
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=[],
        )
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# L1 base — не ранее 8-й недели
# ══════════════════════════════════════════════════════════════════════════════

class TestL1BaseWeekThreshold:

    def test_week_7_too_early(self):
        ok = can_add_intensity(
            level=1, period="base", injury_return=False,
            program_week_number=7, growth_streak=5,
            recent_weeks=good_weeks(4),
        )
        assert ok is False

    def test_week_8_ok(self):
        ok = can_add_intensity(
            level=1, period="base", injury_return=False,
            program_week_number=8, growth_streak=5,
            recent_weeks=good_weeks(4),
        )
        assert ok is True

    def test_week_10_ok(self):
        ok = can_add_intensity(
            level=1, period="base", injury_return=False,
            program_week_number=10, growth_streak=3,
            recent_weeks=good_weeks(4),
        )
        assert ok is True


# ══════════════════════════════════════════════════════════════════════════════
# L2 base — нужно 3 успешных недели подряд (growth_streak ≥ 3)
# ══════════════════════════════════════════════════════════════════════════════

class TestL2BaseGrowthStreak:

    def test_streak_2_not_enough(self):
        ok = can_add_intensity(
            level=2, period="base", injury_return=False,
            program_week_number=10, growth_streak=2,
            recent_weeks=good_weeks(4),
        )
        assert ok is False

    def test_streak_3_ok(self):
        ok = can_add_intensity(
            level=2, period="base", injury_return=False,
            program_week_number=10, growth_streak=3,
            recent_weeks=good_weeks(4),
        )
        assert ok is True

    def test_streak_5_ok(self):
        ok = can_add_intensity(
            level=2, period="base", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=good_weeks(4),
        )
        assert ok is True


# ══════════════════════════════════════════════════════════════════════════════
# L2 preparatory — всегда разрешено при хороших условиях
# ══════════════════════════════════════════════════════════════════════════════

class TestL2PreparatoryIntensity:

    def test_l2_preparatory_allowed(self):
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=0,
            recent_weeks=good_weeks(4),
        )
        assert ok is True


# ══════════════════════════════════════════════════════════════════════════════
# Боль блокирует
# ══════════════════════════════════════════════════════════════════════════════

class TestPainBlocks:

    def test_pain_last_week_blocks(self):
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_pain(pain_at=-1),
        )
        assert ok is False

    def test_pain_week_before_last_blocks(self):
        """Боль 2 нед назад тоже блокирует (окно 2 нед)."""
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_pain(pain_at=-2),
        )
        assert ok is False

    def test_pain_4_weeks_ago_doesnt_block(self):
        """Боль 4 нед назад — вне окна блокировки."""
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_pain(pain_at=0),  # 4 нед назад
        )
        assert ok is True


# ══════════════════════════════════════════════════════════════════════════════
# Light/Recovery лимиты
# ══════════════════════════════════════════════════════════════════════════════

class TestLightRecoveryLimits:

    def test_too_many_light_blocks(self):
        """Среднее Light > 2/нед за 4 нед → блок."""
        ok = can_add_intensity(
            level=3, period="base", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_light(light_per_week=3),
        )
        assert ok is False

    def test_2_light_ok(self):
        """Среднее Light = 2/нед — допустимо."""
        ok = can_add_intensity(
            level=3, period="base", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_light(light_per_week=2),
        )
        assert ok is True

    def test_too_many_recovery_blocks(self):
        """Среднее Recovery > 1/нед → блок."""
        ok = can_add_intensity(
            level=3, period="base", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_recovery(rec_per_week=2),
        )
        assert ok is False

    def test_1_recovery_ok(self):
        """Среднее Recovery = 1/нед — допустимо."""
        ok = can_add_intensity(
            level=3, period="base", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks_with_recovery(rec_per_week=1),
        )
        assert ok is True


# ══════════════════════════════════════════════════════════════════════════════
# MAX_INTENSITY_PER_WEEK константы
# ══════════════════════════════════════════════════════════════════════════════

class TestMaxIntensityConstants:

    def test_l1_base_in_max_is_0(self):
        assert MAX_INTENSITY_PER_WEEK[("L1", "base_in")] == 0

    def test_l1_base_max_is_1(self):
        assert MAX_INTENSITY_PER_WEEK[("L1", "base")] == 1

    def test_l1_specialized_max_is_2(self):
        assert MAX_INTENSITY_PER_WEEK[("L1", "specialized")] == 2

    def test_l2_base_max_is_1(self):
        assert MAX_INTENSITY_PER_WEEK[("L2", "base")] == 1

    def test_l2_preparatory_max_is_2(self):
        assert MAX_INTENSITY_PER_WEEK[("L2", "preparatory")] == 2

    def test_l3_regular_base_max_is_2(self):
        assert MAX_INTENSITY_PER_WEEK[("L3_REGULAR", "base")] == 2

    def test_l3_regular_prep_max_is_2(self):
        assert MAX_INTENSITY_PER_WEEK[("L3_REGULAR", "preparatory")] == 2

    def test_l3_regular_recovery_period_is_0(self):
        assert MAX_INTENSITY_PER_WEEK[("L3_REGULAR", "recovery_period")] == 0

    def test_l3_return_base_max_is_1(self):
        assert MAX_INTENSITY_PER_WEEK[("L3_RETURN", "base")] == 1

    def test_l3_return_prep_max_is_2(self):
        assert MAX_INTENSITY_PER_WEEK[("L3_RETURN", "preparatory")] == 2

    def test_max_intervals_per_week_is_1(self):
        assert MAX_INTERVALS_PER_WEEK == 1


# ══════════════════════════════════════════════════════════════════════════════
# L3 regular/return
# ══════════════════════════════════════════════════════════════════════════════

class TestL3RegularIntensity:

    def test_l3_regular_base_allowed(self):
        ok = can_add_intensity(
            level=3, period="base", injury_return=False,
            program_week_number=5, growth_streak=0,
            recent_weeks=good_weeks(4),
        )
        assert ok is True

    def test_l3_return_base_allowed(self):
        ok = can_add_intensity(
            level=3, period="base", injury_return=True,
            program_week_number=5, growth_streak=0,
            recent_weeks=good_weeks(4),
        )
        assert ok is True

    def test_l3_return_prep_allowed(self):
        ok = can_add_intensity(
            level=3, period="preparatory", injury_return=True,
            program_week_number=8, growth_streak=3,
            recent_weeks=good_weeks(4),
        )
        assert ok is True
