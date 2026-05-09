"""
tests/test_engine/test_red_flags.py

Тесты engine/red_flags.py (spec раздел 3.11).
Функции:
  detect_high_pain_streak  — 3 дня pain==3 подряд → True
  detect_mild_pain_streak  — 3 дня pain==2 подряд → True
  count_high_pain_streak   — текущая серия pain==3 с конца
  count_mild_pain_streak   — текущая серия pain==2 с конца
Правило: NULL (нет чек-ина) сбрасывает счётчик.
"""
import pytest
from engine.red_flags import (
    DayPainData,
    detect_high_pain_streak,
    detect_mild_pain_streak,
    count_high_pain_streak,
    count_mild_pain_streak,
)


def d(pain: int | None) -> DayPainData:
    """Создаёт DayPainData с заданным уровнем боли."""
    return DayPainData(pain_level=pain)


# ══════════════════════════════════════════════════════════════════════════════
# detect_high_pain_streak — red flag
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectHighPainStreak:

    def test_three_pain3_triggers(self):
        """3 дня pain==3 подряд → red flag."""
        days = [d(3), d(3), d(3)]
        assert detect_high_pain_streak(days) is True

    def test_four_pain3_triggers(self):
        """4 дня подряд тоже активирует."""
        days = [d(3), d(3), d(3), d(3)]
        assert detect_high_pain_streak(days) is True

    def test_two_pain3_not_enough(self):
        """2 дня pain==3 — недостаточно (порог = 3)."""
        days = [d(3), d(3)]
        assert detect_high_pain_streak(days) is False

    def test_null_breaks_streak(self):
        """NULL (нет чек-ина) сбрасывает серию."""
        days = [d(3), d(None), d(3), d(3)]
        assert detect_high_pain_streak(days) is False

    def test_pain2_in_middle_breaks_streak(self):
        """pain==2 прерывает серию pain==3."""
        days = [d(3), d(2), d(3), d(3)]
        assert detect_high_pain_streak(days) is False

    def test_pain1_in_middle_breaks_streak(self):
        days = [d(1), d(3), d(3), d(3)]
        # Последние 3 — all pain==3 → True
        assert detect_high_pain_streak(days) is True

    def test_pain1_at_end_breaks_streak(self):
        """pain==1 на конце — серия прервана."""
        days = [d(3), d(3), d(3), d(1)]
        assert detect_high_pain_streak(days) is False

    def test_empty_list(self):
        assert detect_high_pain_streak([]) is False

    def test_single_pain3(self):
        assert detect_high_pain_streak([d(3)]) is False

    def test_custom_days_param(self):
        """days=2 → 2 подряд достаточно."""
        assert detect_high_pain_streak([d(3), d(3)], days=2) is True

    def test_all_pain1_no_trigger(self):
        days = [d(1), d(1), d(1)]
        assert detect_high_pain_streak(days) is False

    def test_null_only(self):
        days = [d(None), d(None), d(None)]
        assert detect_high_pain_streak(days) is False


# ══════════════════════════════════════════════════════════════════════════════
# detect_mild_pain_streak — блокировка роста (не откат)
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectMildPainStreak:

    def test_three_pain2_triggers(self):
        """3 дня pain==2 подряд → блок роста."""
        days = [d(2), d(2), d(2)]
        assert detect_mild_pain_streak(days) is True

    def test_two_pain2_not_enough(self):
        days = [d(2), d(2)]
        assert detect_mild_pain_streak(days) is False

    def test_null_breaks_mild_streak(self):
        days = [d(2), d(None), d(2), d(2)]
        assert detect_mild_pain_streak(days) is False

    def test_pain3_breaks_mild_streak(self):
        """pain==3 (хуже) не считается как pain==2 серия."""
        days = [d(2), d(3), d(2), d(2)]
        assert detect_mild_pain_streak(days) is False

    def test_pain1_breaks_mild_streak(self):
        days = [d(2), d(2), d(1), d(2)]
        assert detect_mild_pain_streak(days) is False

    def test_four_pain2_window_of_3(self):
        """4 дня pain==2 — последние 3 тоже pain==2 → True."""
        days = [d(2), d(2), d(2), d(2)]
        assert detect_mild_pain_streak(days) is True

    def test_pain2_then_pain1_at_end(self):
        days = [d(2), d(2), d(2), d(1)]
        assert detect_mild_pain_streak(days) is False

    def test_empty_list(self):
        assert detect_mild_pain_streak([]) is False

    def test_custom_days_param(self):
        assert detect_mild_pain_streak([d(2), d(2)], days=2) is True


# ══════════════════════════════════════════════════════════════════════════════
# count_high_pain_streak — текущая серия pain==3 с конца
# ══════════════════════════════════════════════════════════════════════════════

class TestCountHighPainStreak:

    def test_three_at_end(self):
        days = [d(1), d(3), d(3), d(3)]
        assert count_high_pain_streak(days) == 3

    def test_two_at_end(self):
        days = [d(3), d(3), d(3), d(1), d(3), d(3)]
        assert count_high_pain_streak(days) == 2

    def test_none_at_end_resets(self):
        days = [d(3), d(3), d(3), d(None)]
        assert count_high_pain_streak(days) == 0

    def test_no_pain3(self):
        days = [d(1), d(2), d(1)]
        assert count_high_pain_streak(days) == 0

    def test_empty(self):
        assert count_high_pain_streak([]) == 0

    def test_single_pain3(self):
        assert count_high_pain_streak([d(3)]) == 1

    def test_all_pain3(self):
        days = [d(3)] * 5
        assert count_high_pain_streak(days) == 5


# ══════════════════════════════════════════════════════════════════════════════
# count_mild_pain_streak — текущая серия pain==2 с конца
# ══════════════════════════════════════════════════════════════════════════════

class TestCountMildPainStreak:

    def test_three_at_end(self):
        days = [d(1), d(2), d(2), d(2)]
        assert count_mild_pain_streak(days) == 3

    def test_broken_by_pain3(self):
        days = [d(2), d(2), d(3), d(2)]
        assert count_mild_pain_streak(days) == 1

    def test_none_resets(self):
        days = [d(2), d(2), d(None)]
        assert count_mild_pain_streak(days) == 0

    def test_empty(self):
        assert count_mild_pain_streak([]) == 0

    def test_all_pain2(self):
        days = [d(2)] * 4
        assert count_mild_pain_streak(days) == 4
