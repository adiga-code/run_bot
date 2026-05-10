"""
tests/test_engine/test_long_calculations.py

Тесты расчёта long-тренировок (spec раздел 3.6).

L1 стадия 1 (зависимый long):
  long = min(avg × 1.3, target × 0.35)

L1 стадия 2 (независимый long):
  long = min(target × 0.35, ceiling)

L2:
  long = min(target × 0.35, ceiling)

L3 regular base:
  long ≤ 35% от недели

L3 regular preparatory:
  long ≤ 40% от недели

L3 after break:
  long ≤ 35% (как L2)
"""
import pytest
from engine.week_planner import split_running_minutes
from engine.constants import (
    L1_LONG_MAX_RATIO, L2_LONG_MAX_RATIO,
    L3_REGULAR_LONG_RATIO_BASE, L3_REGULAR_LONG_RATIO_PREP,
    L1_LONG_RATIO_DEPENDENT,
    round_int,
)


# ══════════════════════════════════════════════════════════════════════════════
# L1 стадия 1 — зависимый long
# ══════════════════════════════════════════════════════════════════════════════

class TestL1Stage1Long:

    def _calc(self, target: int, n_run: int = 3) -> int:
        mins = split_running_minutes(
            weekly_target=target,
            level=1, period="base_in",
            injury_return=False,
            n_run_days=n_run,
            is_long_independent=False,
            is_recovery_week=False,
        )
        return mins["long"]

    def test_long_formula_stage1(self):
        """long = min(avg × 1.3, target × 0.35)."""
        target = 150
        n_run = 3
        avg = target / n_run  # 50
        expected = min(round_int(avg * L1_LONG_RATIO_DEPENDENT), round_int(target * L1_LONG_MAX_RATIO))
        actual = self._calc(target, n_run)
        assert actual == expected

    def test_long_capped_at_35_percent(self):
        """long не превышает 35% от цели."""
        target = 300  # большой объём → формула avg × 1.3 может превысить 35%
        long = self._calc(target, n_run=3)
        assert long <= round_int(target * L1_LONG_MAX_RATIO) + 1

    def test_long_reasonable_for_small_volume(self):
        """При малом объёме long выглядит разумно."""
        long = self._calc(60, n_run=3)
        assert long > 0
        assert long <= round_int(60 * 0.35) + 1

    def test_long_with_4_run_days(self):
        long = self._calc(180, n_run=4)
        assert long <= round_int(180 * 0.35) + 1
        assert long > 0


# ══════════════════════════════════════════════════════════════════════════════
# L1 стадия 2 — независимый long
# ══════════════════════════════════════════════════════════════════════════════

class TestL1Stage2Long:

    def _calc(self, target: int, n_run: int = 3) -> int:
        mins = split_running_minutes(
            weekly_target=target,
            level=1, period="base",
            injury_return=False,
            n_run_days=n_run,
            is_long_independent=True,
            is_recovery_week=False,
        )
        return mins["long"]

    def test_long_35_percent_stage2(self):
        """Стадия 2: long = target × 0.35."""
        target = 200
        expected = round_int(target * L1_LONG_MAX_RATIO)
        actual = self._calc(target)
        assert actual == expected

    def test_long_at_180_target(self):
        long = self._calc(180)
        assert long == round_int(180 * 0.35)

    def test_long_at_240_ceiling(self):
        """При объёме близком к потолку long не превышает 35%."""
        long = self._calc(240)
        assert long <= round_int(240 * 0.35) + 1


# ══════════════════════════════════════════════════════════════════════════════
# L2
# ══════════════════════════════════════════════════════════════════════════════

class TestL2Long:

    def _calc(self, target: int, n_run: int = 4) -> int:
        mins = split_running_minutes(
            weekly_target=target,
            level=2, period="base",
            injury_return=False,
            n_run_days=n_run,
            is_long_independent=False,
            is_recovery_week=False,
        )
        return mins["long"]

    def test_long_35_percent_l2(self):
        target = 200
        long = self._calc(target)
        assert long == round_int(target * L2_LONG_MAX_RATIO)

    def test_long_at_300_l2(self):
        long = self._calc(300)
        assert long <= round_int(300 * 0.35) + 1

    def test_l2_long_ratio_is_35(self):
        assert L2_LONG_MAX_RATIO == pytest.approx(0.35)


# ══════════════════════════════════════════════════════════════════════════════
# L3 regular
# ══════════════════════════════════════════════════════════════════════════════

class TestL3RegularLong:

    def _calc(self, target: int, period: str = "base", n_run: int = 5) -> int:
        mins = split_running_minutes(
            weekly_target=target,
            level=3, period=period,
            injury_return=False,
            n_run_days=n_run,
            is_long_independent=False,
            is_recovery_week=False,
        )
        return mins["long"]

    def test_l3_base_35_percent(self):
        """L3 regular base: long ≤ 35%."""
        target = 300
        long = self._calc(target, period="base")
        assert long == round_int(target * L3_REGULAR_LONG_RATIO_BASE)

    def test_l3_preparatory_40_percent(self):
        """L3 regular preparatory: long ≤ 40%."""
        target = 360
        long = self._calc(target, period="preparatory")
        assert long == round_int(target * L3_REGULAR_LONG_RATIO_PREP)

    def test_l3_prep_ratio_bigger_than_base(self):
        """preparatory допускает больший long, чем base."""
        assert L3_REGULAR_LONG_RATIO_PREP > L3_REGULAR_LONG_RATIO_BASE

    def test_l3_regular_long_ratio_constants(self):
        assert L3_REGULAR_LONG_RATIO_BASE == pytest.approx(0.35)
        assert L3_REGULAR_LONG_RATIO_PREP == pytest.approx(0.40)

    def test_l3_large_volume_long_capped(self):
        """При большом объёме long не уходит за 40%."""
        target = 500
        long = self._calc(target, period="preparatory")
        assert long <= round_int(target * 0.40) + 1


# ══════════════════════════════════════════════════════════════════════════════
# L3 after break
# ══════════════════════════════════════════════════════════════════════════════

class TestL3ReturnLong:

    def _calc(self, target: int, n_run: int = 4) -> int:
        mins = split_running_minutes(
            weekly_target=target,
            level=3, period="base",
            injury_return=True,
            n_run_days=n_run,
            is_long_independent=False,
            is_recovery_week=False,
        )
        return mins["long"]

    def test_l3_return_35_percent(self):
        """L3 after break: long ≤ 35% (как L2)."""
        target = 200
        long = self._calc(target)
        assert long <= round_int(target * 0.35) + 1

    def test_l3_return_long_positive(self):
        long = self._calc(200)
        assert long > 0


# ══════════════════════════════════════════════════════════════════════════════
# Граничные случаи
# ══════════════════════════════════════════════════════════════════════════════

class TestLongEdgeCases:

    def test_1_run_day_only_long(self):
        """Если только 1 беговой день — он становится long."""
        mins = split_running_minutes(
            weekly_target=100,
            level=1, period="base",
            injury_return=False,
            n_run_days=1,
            is_long_independent=True,
            is_recovery_week=False,
        )
        assert mins["long"] > 0
        assert mins["easy"] == 0

    def test_long_never_exceeds_target(self):
        """long никогда не превышает weekly_target."""
        for target in [60, 120, 180, 240]:
            mins = split_running_minutes(
                weekly_target=target, level=1, period="base",
                injury_return=False, n_run_days=3,
                is_long_independent=True, is_recovery_week=False,
            )
            assert mins["long"] <= target
