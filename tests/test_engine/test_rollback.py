"""
tests/test_engine/test_rollback.py

Тесты механизма red_flag и отката объёма (spec раздел 3.11).

  - 3 дня pain==3 подряд в evaluate_week → triggers_rollback=True
  - decide_next_week при red_flag_active → is_rollback=True, volume=last_successful
  - Без last_successful_volume → откат на стартовый объём уровня
  - Откат не ниже потолка и не выше ceiling
  - red_flag не мешает детекции других условий (completion_rate, etc.)
"""
import pytest
from types import SimpleNamespace
from engine.week_evaluator import evaluate_week, decide_next_week, WeekEvaluation
from engine.red_flags import DayPainData, detect_high_pain_streak
from engine.constants import L1_START_VOLUME_BASE, L2_START_VOLUME, ROLLBACK_PAIN_DAYS


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_day_plan(dow: int, day_type: str = "run", is_key: bool = False,
                  planned_minutes: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=dow, day_type=day_type,
        is_key=is_key, planned_minutes=planned_minutes,
    )


def make_week_plan(days, period: str = "base",
                   weekly_target_minutes: int = 200,
                   is_recovery_week: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        days=days, period=period,
        is_recovery_period=False,
        weekly_target_minutes=weekly_target_minutes,
        is_recovery_week=is_recovery_week,
    )


def make_log(dow: int, status: str = "done", pain: int = 1,
             checkin_done: bool = True, version: str = "base",
             planned_minutes: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=dow, completion_status=status,
        pain_level=pain, checkin_done=checkin_done,
        assigned_version=version, planned_minutes=planned_minutes,
    )


def make_user(level: int = 2, red_flag_active: bool = False,
              last_successful_volume: int | None = None,
              injury_return: bool = False,
              entry_point: str = "base",
              peak_volume_minutes: int = 200,
              growth_streak: int = 0, weeks_since_recovery: int = 0,
              macrocycle_peak_volume: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        level=level,
        injury_return_active=injury_return,
        red_flag_active=red_flag_active,
        last_successful_volume=last_successful_volume,
        entry_point=entry_point,
        peak_volume_minutes=peak_volume_minutes,
        growth_streak=growth_streak,
        weeks_since_recovery=weeks_since_recovery,
        macrocycle_peak_volume=macrocycle_peak_volume,
        weekly_target_minutes=peak_volume_minutes,
    )


# ══════════════════════════════════════════════════════════════════════════════
# detect_high_pain_streak (в evaluate_week через DayPainData)
# ══════════════════════════════════════════════════════════════════════════════

class TestTriggerRollbackDetection:

    def test_3_consecutive_pain3_triggers_rollback(self):
        """3 дня подряд pain==3 в неделе → triggers_rollback=True."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain=3) for i in [1, 2, 3]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True

    def test_2_consecutive_pain3_no_rollback(self):
        """2 дня pain==3 — недостаточно."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain=3),
            make_log(2, "done", pain=3),
            make_log(3, "done", pain=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is False

    def test_pain3_with_gap_no_rollback(self):
        """3 дня pain==3, но с пропуском (нет чек-ина) — серия сброшена."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3, 4]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain=3, checkin_done=True),
            make_log(2, "done", pain=3, checkin_done=False),  # нет чек-ина
            make_log(3, "done", pain=3, checkin_done=True),
            make_log(4, "done", pain=3, checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        # Серия: checkin_done=False → pain_level=None → сброс
        # Последовательность: 3, None, 3, 3 → серия из 2, не 3
        assert eval_.triggers_rollback is False

    def test_pain3_in_4_consecutive_days_triggers(self):
        """4 дня подряд pain==3 → triggers_rollback=True."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3, 4]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain=3) for i in [1, 2, 3, 4]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True

    def test_rollback_in_recovery_period_still_detected(self):
        """В recovery_period triggers_rollback всё равно детектируется."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3]]
        week = make_week_plan(days, period="recovery_period")
        week = SimpleNamespace(
            days=days, period="recovery_period",
            is_recovery_period=True,
            weekly_target_minutes=120,
            is_recovery_week=False,
        )
        logs = [make_log(i, "done", pain=3) for i in [1, 2, 3]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True
        assert eval_.growth_eligible is False


# ══════════════════════════════════════════════════════════════════════════════
# detect_high_pain_streak (напрямую)
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectHighPainStreakDirect:

    def _d(self, pain: int | None) -> DayPainData:
        return DayPainData(pain_level=pain)

    def test_constant_rollback_pain_days_is_3(self):
        assert ROLLBACK_PAIN_DAYS == 3

    def test_threshold_exactly_3(self):
        days = [self._d(3)] * 3
        assert detect_high_pain_streak(days, days=ROLLBACK_PAIN_DAYS) is True

    def test_threshold_2(self):
        days = [self._d(3), self._d(3)]
        assert detect_high_pain_streak(days, days=ROLLBACK_PAIN_DAYS) is False

    def test_null_in_streak_resets(self):
        days = [self._d(3), self._d(None), self._d(3), self._d(3), self._d(3)]
        # Последние 3 — all pain==3 → True
        assert detect_high_pain_streak(days, days=3) is True

    def test_null_at_end(self):
        days = [self._d(3), self._d(3), self._d(3), self._d(None)]
        assert detect_high_pain_streak(days, days=3) is False


# ══════════════════════════════════════════════════════════════════════════════
# decide_next_week — red_flag_active
# ══════════════════════════════════════════════════════════════════════════════

def _good_eval(actual: int = 200) -> WeekEvaluation:
    return WeekEvaluation(
        completion_rate=1.0, keys_completed=True,
        had_high_pain=False, high_pain_streak=0, mild_pain_streak=0,
        light_days=0, recovery_days=0, actual_minutes=actual,
        growth_eligible=True, no_growth_reason=None,
        triggers_rollback=False, in_recovery_period=False,
    )


class TestRedFlagDecision:

    def test_red_flag_forces_rollback_to_last_successful(self):
        user = make_user(level=2, red_flag_active=True, last_successful_volume=160)
        week = make_week_plan(
            [make_day_plan(1, is_key=True)],
            period="base", weekly_target_minutes=220,
        )
        decision = decide_next_week(user, week, _good_eval(220))
        assert decision.is_rollback is True
        assert decision.next_target_minutes == 160

    def test_red_flag_no_last_vol_uses_level_start(self):
        """Нет last_successful_volume → стартовый объём уровня."""
        user = make_user(level=2, red_flag_active=True, last_successful_volume=None, entry_point="base")
        week = make_week_plan(
            [make_day_plan(1, is_key=True)],
            period="preparatory", weekly_target_minutes=300,
        )
        decision = decide_next_week(user, week, _good_eval(300))
        assert decision.is_rollback is True
        assert decision.next_target_minutes == L2_START_VOLUME

    def test_red_flag_l1_no_last_vol(self):
        user = make_user(level=1, red_flag_active=True, last_successful_volume=None, entry_point="base")
        week = make_week_plan(
            [make_day_plan(1, is_key=True)],
            period="base", weekly_target_minutes=200,
        )
        decision = decide_next_week(user, week, _good_eval(200))
        assert decision.is_rollback is True
        assert decision.next_target_minutes == L1_START_VOLUME_BASE

    def test_no_red_flag_no_rollback(self):
        user = make_user(level=2, red_flag_active=False, peak_volume_minutes=200)
        week = make_week_plan(
            [make_day_plan(1, is_key=True)],
            period="base", weekly_target_minutes=200,
        )
        decision = decide_next_week(user, week, _good_eval(200))
        assert decision.is_rollback is False

    def test_red_flag_overrides_growth_eligible(self):
        """Даже если growth_eligible=True, red_flag принудительно откатывает."""
        user = make_user(level=2, red_flag_active=True, last_successful_volume=150,
                         growth_streak=3)
        week = make_week_plan(
            [make_day_plan(1, is_key=True)],
            period="preparatory", weekly_target_minutes=280,
        )
        eval_ = _good_eval(280)
        decision = decide_next_week(user, week, eval_)
        assert decision.is_rollback is True
        assert decision.next_target_minutes == 150
        # После отката не должно быть разгрузочной
        assert decision.is_recovery_week is False
