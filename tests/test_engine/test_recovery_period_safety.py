"""
tests/test_engine/test_recovery_period_safety.py

Тесты безопасности recovery_period (spec раздел 3.4.3):
  - В recovery_period growth_eligible всегда False
  - В recovery_period no_growth_reason == "recovery_period"
  - В recovery_period объём снижается на RECOVERY_MULTIPLIER (×0.6 от mac_peak)
  - triggers_rollback детектируется даже в recovery_period
  - is_recovery_week == False при recovery_period (это разные вещи!)
  - L2 и L3 return: recovery_period не применяется (одна разгрузочная нед)
"""
import pytest
from types import SimpleNamespace
from engine.week_evaluator import evaluate_week, decide_next_week, WeekEvaluation
from engine.constants import RECOVERY_MULTIPLIER


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_day_plan(dow: int, day_type: str = "run", is_key: bool = False,
                  planned_minutes: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=dow, day_type=day_type,
        is_key=is_key, planned_minutes=planned_minutes,
    )


def make_week_plan(days, period: str = "recovery_period",
                   is_recovery_period: bool = True,
                   weekly_target_minutes: int = 200) -> SimpleNamespace:
    return SimpleNamespace(
        days=days, period=period,
        is_recovery_period=is_recovery_period,
        weekly_target_minutes=weekly_target_minutes,
        is_recovery_week=False,
    )


def make_log(dow: int, status: str = "done", pain: int = 1,
             checkin_done: bool = True, version: str = "base",
             planned_minutes: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=dow, completion_status=status,
        pain_level=pain, checkin_done=checkin_done,
        assigned_version=version, planned_minutes=planned_minutes,
    )


def make_user(level: int = 3, injury_return: bool = False,
              macrocycle_peak_volume: int = 400,
              weekly_target_minutes: int = 240,
              growth_streak: int = 0, weeks_since_recovery: int = 0,
              red_flag_active: bool = False,
              peak_volume_minutes: int = 400) -> SimpleNamespace:
    return SimpleNamespace(
        level=level, injury_return_active=injury_return,
        macrocycle_peak_volume=macrocycle_peak_volume,
        weekly_target_minutes=weekly_target_minutes,
        growth_streak=growth_streak,
        weeks_since_recovery=weeks_since_recovery,
        red_flag_active=red_flag_active,
        peak_volume_minutes=peak_volume_minutes,
        last_successful_volume=None, entry_point="base",
    )


def perfect_logs(days: list[SimpleNamespace]) -> list[SimpleNamespace]:
    return [
        make_log(d.day_of_week, "done", pain=1, version="base", planned_minutes=d.planned_minutes)
        for d in days if d.day_type != "rest"
    ]


# ══════════════════════════════════════════════════════════════════════════════
# evaluate_week в recovery_period
# ══════════════════════════════════════════════════════════════════════════════

class TestEvaluateWeekInRecoveryPeriod:

    def test_growth_always_false(self):
        """В recovery_period growth_eligible всегда False."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = perfect_logs(days)
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False

    def test_no_growth_reason_is_recovery_period(self):
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = perfect_logs(days)
        eval_ = evaluate_week(week, logs)
        assert eval_.no_growth_reason == "recovery_period"

    def test_in_recovery_period_flag_set(self):
        days = [make_day_plan(i, "run") for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = perfect_logs(days)
        eval_ = evaluate_week(week, logs)
        assert eval_.in_recovery_period is True

    def test_perfect_week_still_no_growth(self):
        """Даже идеальная неделя в recovery_period не даёт роста."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain=1, version="base") for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False
        # Но completion_rate может быть 100%
        assert eval_.completion_rate == pytest.approx(1.0)

    def test_triggers_rollback_still_detected(self):
        """В recovery_period triggers_rollback всё равно работает."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain=3, checkin_done=True) for i in [1, 2, 3]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True
        assert eval_.growth_eligible is False  # по-прежнему False

    def test_zero_pain_no_rollback(self):
        days = [make_day_plan(i, "run") for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain=1) for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is False


# ══════════════════════════════════════════════════════════════════════════════
# decide_next_week в recovery_period
# ══════════════════════════════════════════════════════════════════════════════

class TestDecideNextWeekInRecoveryPeriod:

    def _eval_recovery(self, actual_minutes: int = 120) -> WeekEvaluation:
        return WeekEvaluation(
            completion_rate=1.0, keys_completed=True,
            had_high_pain=False, high_pain_streak=0, mild_pain_streak=0,
            light_days=0, recovery_days=0, actual_minutes=actual_minutes,
            growth_eligible=False, no_growth_reason="recovery_period",
            triggers_rollback=False, in_recovery_period=True,
        )

    def test_volume_is_mac_peak_times_recovery_multiplier(self):
        """В recovery_period объём = mac_peak × 0.6."""
        user = make_user(level=3, macrocycle_peak_volume=400, peak_volume_minutes=400)
        week = SimpleNamespace(
            period="recovery_period",
            weekly_target_minutes=240,
            is_recovery_week=False,
        )
        eval_ = self._eval_recovery()
        decision = decide_next_week(user, week, eval_)
        # 400 × 0.6 = 240
        assert decision.next_target_minutes == pytest.approx(240, abs=2)

    def test_not_rollback_in_recovery_period(self):
        """В recovery_period это не откат (is_rollback=False)."""
        user = make_user(level=3, macrocycle_peak_volume=400)
        week = SimpleNamespace(
            period="recovery_period",
            weekly_target_minutes=240,
            is_recovery_week=False,
        )
        eval_ = self._eval_recovery()
        decision = decide_next_week(user, week, eval_)
        assert decision.is_rollback is False

    def test_not_recovery_week_flag(self):
        """В recovery_period is_recovery_week=False в решении."""
        user = make_user(level=3, macrocycle_peak_volume=400)
        week = SimpleNamespace(
            period="recovery_period",
            weekly_target_minutes=240,
            is_recovery_week=False,
        )
        eval_ = self._eval_recovery()
        decision = decide_next_week(user, week, eval_)
        assert decision.is_recovery_week is False

    def test_volume_capped_by_ceiling(self):
        """Объём не превышает потолок уровня."""
        from engine.constants import L3_REGULAR_CEILING
        user = make_user(level=3, macrocycle_peak_volume=L3_REGULAR_CEILING + 100)
        week = SimpleNamespace(
            period="recovery_period",
            weekly_target_minutes=300,
            is_recovery_week=False,
        )
        eval_ = self._eval_recovery()
        decision = decide_next_week(user, week, eval_)
        assert decision.next_target_minutes <= L3_REGULAR_CEILING

    def test_recovery_multiplier_is_0_6(self):
        """Константа RECOVERY_MULTIPLIER == 0.6."""
        assert RECOVERY_MULTIPLIER == pytest.approx(0.60)


# ══════════════════════════════════════════════════════════════════════════════
# is_recovery_period vs is_recovery_week — разные концепции
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoveryPeriodVsWeek:

    def test_regular_week_in_base_is_not_recovery_period(self):
        """Обычная неделя в base → in_recovery_period=False."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = SimpleNamespace(
            days=days, period="base",
            is_recovery_period=False,
            weekly_target_minutes=200,
            is_recovery_week=False,
        )
        logs = [make_log(i, "done", pain=1) for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.in_recovery_period is False

    def test_recovery_week_in_base_is_not_recovery_period(self):
        """Разгрузочная неделя в base ≠ recovery_period."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = SimpleNamespace(
            days=days, period="base",
            is_recovery_period=False,  # НЕ recovery_period!
            weekly_target_minutes=120,
            is_recovery_week=True,    # разгрузочная
        )
        logs = [make_log(i, "done", pain=1) for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.in_recovery_period is False
        # Рост может быть eligible (если все условия выполнены)
        assert eval_.growth_eligible is True
