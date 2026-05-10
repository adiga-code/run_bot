"""
tests/test_engine/test_progression.py

Тесты прогрессии объёма (spec раздел 3.9).
  - decide_next_week: расчёт next_target_minutes
  - +10% при успешной неделе (L1, L2, L3 base)
  - +15% при L3 regular preparatory
  - Разгрузочная неделя × 0.6 (RECOVERY_MULTIPLIER)
  - Потолки: L1=240, L2=300, L3_regular=600, L3_return=420
  - growth_streak==3 → принудительная разгрузочная
  - weeks_since_recovery==6 → failsafe разгрузка
  - red_flag_active → откат на last_successful_volume
"""
import pytest
from types import SimpleNamespace
from engine.week_evaluator import decide_next_week, WeekEvaluation, NextWeekDecision
from engine.constants import (
    L1_CEILING, L2_CEILING, L3_REGULAR_CEILING, L3_RETURN_CEILING,
    GROWTH_MULTIPLIER, RECOVERY_MULTIPLIER,
    GROWTH_STREAK_FOR_RECOVERY, FAILSAFE_WEEKS_WITHOUT_RECOVERY,
    get_level_ceiling,
)


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_user(
    level: int = 2,
    injury_return: bool = False,
    growth_streak: int = 0,
    weeks_since_recovery: int = 0,
    red_flag_active: bool = False,
    peak_volume_minutes: int = 200,
    macrocycle_peak_volume: int | None = None,
    weekly_target_minutes: int = 200,
    last_successful_volume: int | None = None,
    entry_point: str = "base",
) -> SimpleNamespace:
    return SimpleNamespace(
        level=level,
        injury_return_active=injury_return,
        growth_streak=growth_streak,
        weeks_since_recovery=weeks_since_recovery,
        red_flag_active=red_flag_active,
        peak_volume_minutes=peak_volume_minutes,
        macrocycle_peak_volume=macrocycle_peak_volume,
        weekly_target_minutes=weekly_target_minutes,
        last_successful_volume=last_successful_volume,
        entry_point=entry_point,
    )


def make_week_plan(
    period: str = "base",
    weekly_target_minutes: int = 200,
    is_recovery_week: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        period=period,
        weekly_target_minutes=weekly_target_minutes,
        is_recovery_week=is_recovery_week,
    )


def good_eval(actual_minutes: int = 200) -> WeekEvaluation:
    return WeekEvaluation(
        completion_rate=1.0,
        keys_completed=True,
        had_high_pain=False,
        high_pain_streak=0,
        mild_pain_streak=0,
        light_days=0,
        recovery_days=0,
        actual_minutes=actual_minutes,
        growth_eligible=True,
        no_growth_reason=None,
        triggers_rollback=False,
        in_recovery_period=False,
    )


def bad_eval(actual_minutes: int = 180) -> WeekEvaluation:
    return WeekEvaluation(
        completion_rate=0.6,
        keys_completed=False,
        had_high_pain=False,
        high_pain_streak=0,
        mild_pain_streak=0,
        light_days=0,
        recovery_days=0,
        actual_minutes=actual_minutes,
        growth_eligible=False,
        no_growth_reason="completion 60% < 85%",
        triggers_rollback=False,
        in_recovery_period=False,
    )


def recovery_period_eval() -> WeekEvaluation:
    return WeekEvaluation(
        completion_rate=1.0,
        keys_completed=True,
        had_high_pain=False,
        high_pain_streak=0,
        mild_pain_streak=0,
        light_days=0,
        recovery_days=0,
        actual_minutes=120,
        growth_eligible=False,
        no_growth_reason="recovery_period",
        triggers_rollback=False,
        in_recovery_period=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Рост на 10%
# ══════════════════════════════════════════════════════════════════════════════

class TestGrowthMultiplier:

    def test_l1_10_percent_growth(self):
        """L1: +10% при успешной неделе."""
        user = make_user(level=1, peak_volume_minutes=180, weekly_target_minutes=180)
        week = make_week_plan(period="base", weekly_target_minutes=180)
        eval_ = good_eval(actual_minutes=180)
        decision = decide_next_week(user, week, eval_)
        # actual × 1.10 = 180 × 1.10 = 198
        assert decision.next_target_minutes == pytest.approx(198, abs=2)

    def test_l2_10_percent_growth(self):
        user = make_user(level=2, peak_volume_minutes=200, weekly_target_minutes=200)
        week = make_week_plan(period="base", weekly_target_minutes=200)
        eval_ = good_eval(actual_minutes=200)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes == pytest.approx(220, abs=2)

    def test_l3_base_10_percent_growth(self):
        """L3 regular base: +10%."""
        user = make_user(level=3, injury_return=False, peak_volume_minutes=300)
        week = make_week_plan(period="base", weekly_target_minutes=300)
        eval_ = good_eval(actual_minutes=300)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes == pytest.approx(330, abs=2)

    def test_l3_preparatory_15_percent_growth(self):
        """L3 regular preparatory: +15%."""
        user = make_user(level=3, injury_return=False, peak_volume_minutes=300)
        week = make_week_plan(period="preparatory", weekly_target_minutes=300)
        eval_ = good_eval(actual_minutes=300)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes == pytest.approx(345, abs=2)

    def test_l3_return_10_percent_not_15(self):
        """L3 after break: +10%, не +15%."""
        user = make_user(level=3, injury_return=True, peak_volume_minutes=200)
        week = make_week_plan(period="preparatory", weekly_target_minutes=200)
        eval_ = good_eval(actual_minutes=200)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes == pytest.approx(220, abs=2)


# ══════════════════════════════════════════════════════════════════════════════
# Удержание объёма при неуспешной неделе
# ══════════════════════════════════════════════════════════════════════════════

class TestHoldOnFailure:

    def test_hold_on_failed_week(self):
        """Неуспешная неделя → объём не растёт (держим current_target)."""
        user = make_user(level=2, peak_volume_minutes=200)
        week = make_week_plan(period="base", weekly_target_minutes=200)
        eval_ = bad_eval(actual_minutes=180)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes == 200  # target не меняется


# ══════════════════════════════════════════════════════════════════════════════
# Потолки объёма
# ══════════════════════════════════════════════════════════════════════════════

class TestCeilings:

    def test_l1_ceiling_240(self):
        """L1: не превышаем 240 мин/нед."""
        user = make_user(level=1, peak_volume_minutes=235)
        week = make_week_plan(period="base", weekly_target_minutes=235)
        eval_ = good_eval(actual_minutes=235)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes <= L1_CEILING

    def test_l2_ceiling_300(self):
        """L2: не превышаем 300 мин/нед."""
        user = make_user(level=2, peak_volume_minutes=295)
        week = make_week_plan(period="preparatory", weekly_target_minutes=295)
        eval_ = good_eval(actual_minutes=295)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes <= L2_CEILING

    def test_l3_regular_ceiling_600(self):
        """L3 regular: потолок 600 мин/нед."""
        user = make_user(level=3, injury_return=False, peak_volume_minutes=590)
        week = make_week_plan(period="preparatory", weekly_target_minutes=590)
        eval_ = good_eval(actual_minutes=590)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes <= L3_REGULAR_CEILING

    def test_l3_return_ceiling_420(self):
        """L3 after break: потолок 420 мин/нед."""
        user = make_user(level=3, injury_return=True, peak_volume_minutes=415)
        week = make_week_plan(period="preparatory", weekly_target_minutes=415)
        eval_ = good_eval(actual_minutes=415)
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes <= L3_RETURN_CEILING

    def test_ceiling_constants(self):
        """Проверка самих констант."""
        assert L1_CEILING == 240
        assert L2_CEILING == 300
        assert L3_REGULAR_CEILING == 600
        assert L3_RETURN_CEILING == 420


# ══════════════════════════════════════════════════════════════════════════════
# Разгрузочная неделя
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoveryWeek:

    def test_growth_streak_3_triggers_unload(self):
        """growth_streak==3 → разгрузочная неделя."""
        user = make_user(
            level=2,
            growth_streak=GROWTH_STREAK_FOR_RECOVERY,  # =3
            weeks_since_recovery=2,
            peak_volume_minutes=240,
        )
        week = make_week_plan(period="base", weekly_target_minutes=240)
        eval_ = good_eval(actual_minutes=240)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_recovery_week is True
        # Объём: peak × 0.6 = 240 × 0.6 = 144
        assert decision.next_target_minutes == pytest.approx(144, abs=2)

    def test_failsafe_weeks_triggers_unload(self):
        """weeks_since_recovery==6 → принудительная разгрузка."""
        user = make_user(
            level=2,
            growth_streak=0,
            weeks_since_recovery=FAILSAFE_WEEKS_WITHOUT_RECOVERY,  # =6
            peak_volume_minutes=240,
        )
        week = make_week_plan(period="base", weekly_target_minutes=240)
        eval_ = good_eval(actual_minutes=240)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_recovery_week is True

    def test_after_recovery_week_returns_to_peak_plus_growth(self):
        """После разгрузочной: возврат к пику × growth_mult."""
        user = make_user(level=2, peak_volume_minutes=220)
        week = make_week_plan(period="base", weekly_target_minutes=132, is_recovery_week=True)
        eval_ = good_eval(actual_minutes=132)
        decision = decide_next_week(user, week, eval_)
        # Не разгрузочная + не rollback
        assert decision.is_recovery_week is False
        assert decision.is_rollback is False
        # После разгрузочной: peak × 1.10
        assert decision.next_target_minutes == pytest.approx(242, abs=3)

    def test_recovery_multiplier_is_0_6(self):
        """RECOVERY_MULTIPLIER == 0.6."""
        assert RECOVERY_MULTIPLIER == pytest.approx(0.60)

    def test_growth_streak_2_no_unload(self):
        """growth_streak==2 (< 3) → не разгрузочная."""
        user = make_user(level=2, growth_streak=2, weeks_since_recovery=2, peak_volume_minutes=200)
        week = make_week_plan(period="base", weekly_target_minutes=200)
        eval_ = good_eval(actual_minutes=200)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_recovery_week is False


# ══════════════════════════════════════════════════════════════════════════════
# recovery_period — удержание объёма
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoveryPeriodVolume:

    def test_recovery_period_keeps_volume(self):
        """В recovery_period: next_target = mac_peak × 0.6."""
        user = make_user(
            level=3, injury_return=False,
            macrocycle_peak_volume=400, peak_volume_minutes=400,
        )
        week = make_week_plan(period="recovery_period", weekly_target_minutes=240)
        eval_ = recovery_period_eval()
        decision = decide_next_week(user, week, eval_)
        assert decision.is_recovery_week is False
        assert decision.is_rollback is False
        # 400 × 0.6 = 240
        assert decision.next_target_minutes == pytest.approx(240, abs=2)


# ══════════════════════════════════════════════════════════════════════════════
# Red flag → откат
# ══════════════════════════════════════════════════════════════════════════════

class TestRedFlagRollback:

    def test_red_flag_gives_rollback(self):
        """red_flag_active → next_target = last_successful_volume."""
        user = make_user(
            level=2,
            red_flag_active=True,
            last_successful_volume=180,
            peak_volume_minutes=250,
        )
        week = make_week_plan(period="base", weekly_target_minutes=250)
        eval_ = good_eval(actual_minutes=250)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_rollback is True
        assert decision.next_target_minutes == 180

    def test_red_flag_no_last_vol_uses_start(self):
        """red_flag_active без last_successful_volume → стартовый объём уровня."""
        from engine.constants import L2_START_VOLUME
        user = make_user(
            level=2,
            red_flag_active=True,
            last_successful_volume=None,
            entry_point="base",
        )
        week = make_week_plan(period="preparatory", weekly_target_minutes=300)
        eval_ = good_eval(actual_minutes=300)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_rollback is True
        assert decision.next_target_minutes == L2_START_VOLUME

    def test_no_red_flag_no_rollback(self):
        user = make_user(level=2, red_flag_active=False, last_successful_volume=180)
        week = make_week_plan(period="base", weekly_target_minutes=200)
        eval_ = good_eval(actual_minutes=200)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_rollback is False
