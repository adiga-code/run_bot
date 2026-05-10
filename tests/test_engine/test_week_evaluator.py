"""
tests/test_engine/test_week_evaluator.py

Тесты engine/week_evaluator.py (spec разделы 3.9, 3.11).

Тест 7 условий успешной недели:
  1. ≥85% выполнения
  2. Все ключевые тренировки засчитаны
  3. Нет дней с pain==3
  4. pain==2 ≤ 2 дней подряд
  5. Light ≤ 2 дней
  6. Recovery ≤ 1 дня
  7. Не 3+ дней подряд без чек-ина
  В recovery_period: рост всегда False, red_flag детектируется.
"""
import pytest
from types import SimpleNamespace
from engine.week_evaluator import evaluate_week, decide_next_week, WeekEvaluation, NextWeekDecision


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_day_plan(
    day_of_week: int,
    day_type: str = "run",
    is_key: bool = False,
    planned_minutes: int = 50,
) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=day_of_week,
        day_type=day_type,
        is_key=is_key,
        planned_minutes=planned_minutes,
    )


def make_week_plan(
    days: list[SimpleNamespace],
    period: str = "base",
    is_recovery_period: bool = False,
    weekly_target_minutes: int = 200,
    is_recovery_week: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        days=days,
        period=period,
        is_recovery_period=is_recovery_period,
        weekly_target_minutes=weekly_target_minutes,
        is_recovery_week=is_recovery_week,
    )


def make_log(
    day_of_week: int,
    completion_status: str = "done",
    pain_level: int = 1,
    checkin_done: bool = True,
    assigned_version: str = "base",
    planned_minutes: int = 50,
) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=day_of_week,
        completion_status=completion_status,
        pain_level=pain_level,
        checkin_done=checkin_done,
        assigned_version=assigned_version,
        planned_minutes=planned_minutes,
    )


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


# ── Сценарий «идеальная неделя» ───────────────────────────────────────────────

def make_perfect_week():
    """3 тренировки, 1 ключевая, все выполнены, нет боли."""
    days = [
        make_day_plan(1, "run", is_key=True, planned_minutes=60),
        make_day_plan(3, "strength", is_key=False, planned_minutes=30),
        make_day_plan(5, "run", is_key=False, planned_minutes=50),
    ]
    week = make_week_plan(days, period="base")
    logs = [
        make_log(1, "done", pain_level=1, assigned_version="base", planned_minutes=60),
        make_log(3, "done", pain_level=1, assigned_version="base", planned_minutes=30),
        make_log(5, "done", pain_level=1, assigned_version="base", planned_minutes=50),
    ]
    return week, logs


# ══════════════════════════════════════════════════════════════════════════════
# Условие 1: ≥85% выполнения
# ══════════════════════════════════════════════════════════════════════════════

class TestCompletionRate:

    def test_100_percent_growth_eligible(self):
        week, logs = make_perfect_week()
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is True
        assert eval_.completion_rate == pytest.approx(1.0)

    def test_2_of_3_done_is_not_eligible(self):
        """2/3 = 67% < 85% → не eligible."""
        days = [
            make_day_plan(1, "run", is_key=True),
            make_day_plan(3, "strength"),
            make_day_plan(5, "run"),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1),
            make_log(3, "skipped", pain_level=1),
            make_log(5, "done", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False
        assert "completion" in (eval_.no_growth_reason or "").lower()

    def test_all_skipped_is_not_eligible(self):
        days = [make_day_plan(i, "run") for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [make_log(i, "skipped", pain_level=1) for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.completion_rate == pytest.approx(0.0)
        assert eval_.growth_eligible is False

    def test_completion_rate_calculation(self):
        """completion_rate = done / n_planned (не rest-дни)."""
        days = [
            make_day_plan(1, "run"),
            make_day_plan(2, "rest"),   # не считается
            make_day_plan(3, "run"),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1),
            make_log(3, "skipped", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.completion_rate == pytest.approx(0.5)


# ══════════════════════════════════════════════════════════════════════════════
# Условие 2: ключевые тренировки
# ══════════════════════════════════════════════════════════════════════════════

class TestKeyWorkouts:

    def test_key_not_done_blocks_growth(self):
        """Ключевая тренировка не выполнена → growth_eligible=False."""
        days = [
            make_day_plan(1, "run", is_key=True, planned_minutes=60),
            make_day_plan(3, "run", is_key=False, planned_minutes=50),
            make_day_plan(5, "run", is_key=False, planned_minutes=50),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "skipped", pain_level=1),  # ключевая не выполнена
            make_log(3, "done", pain_level=1),
            make_log(5, "done", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False

    def test_key_as_recovery_version_not_counted(self):
        """Ключевая с версией 'recovery' → не засчитана."""
        days = [
            make_day_plan(1, "run", is_key=True, planned_minutes=60),
            make_day_plan(3, "run", is_key=False, planned_minutes=50),
            make_day_plan(5, "run", is_key=False, planned_minutes=50),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, assigned_version="recovery"),  # не засчитана
            make_log(3, "done", pain_level=1),
            make_log(5, "done", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.keys_completed is False
        assert eval_.growth_eligible is False

    def test_key_done_base_version_counted(self):
        week, logs = make_perfect_week()
        eval_ = evaluate_week(week, logs)
        assert eval_.keys_completed is True


# ══════════════════════════════════════════════════════════════════════════════
# Условие 3: нет pain==3
# ══════════════════════════════════════════════════════════════════════════════

class TestPain3BlocksGrowth:

    def test_pain3_blocks_growth(self):
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=3),  # боль
            make_log(3, "done", pain_level=1),
            make_log(5, "done", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.had_high_pain is True
        assert eval_.growth_eligible is False

    def test_no_pain3_does_not_block(self):
        week, logs = make_perfect_week()
        eval_ = evaluate_week(week, logs)
        assert eval_.had_high_pain is False

    def test_pain3_activates_rollback_after_3_days(self):
        """3 дня подряд pain==3 → triggers_rollback."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain_level=3) for i in [1, 2, 3]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True

    def test_2_days_pain3_no_rollback(self):
        """2 дня pain==3 — не хватает для отката."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=3),
            make_log(2, "done", pain_level=3),
            make_log(3, "done", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is False


# ══════════════════════════════════════════════════════════════════════════════
# Условие 4: mild pain streak (pain==2)
# ══════════════════════════════════════════════════════════════════════════════

class TestMildPainStreak:

    def test_3_days_pain2_blocks_growth(self):
        """3 дня подряд pain==2 → growth blocked (но не rollback)."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain_level=2) for i in [1, 2, 3]]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False
        assert eval_.triggers_rollback is False  # не откат, только блок

    def test_2_days_pain2_no_block(self):
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=2),
            make_log(2, "done", pain_level=2),
            make_log(3, "done", pain_level=1),
        ]
        eval_ = evaluate_week(week, logs)
        # Максимальная серия pain==2 = 2 (дни 1 и 2), но порог = 3
        assert eval_.mild_pain_streak == 2   # серия зафиксирована
        assert eval_.growth_eligible is True  # но не блокирует рост (< 3)


# ══════════════════════════════════════════════════════════════════════════════
# Условие 5: Light ≤ 2 дней
# ══════════════════════════════════════════════════════════════════════════════

class TestLightDaysLimit:

    def test_3_light_days_blocks_growth(self):
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain_level=1, assigned_version="light") for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.light_days == 3
        assert eval_.growth_eligible is False

    def test_2_light_days_allows_growth(self):
        """2 Light-дня — допустимо."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, assigned_version="light"),
            make_log(3, "done", pain_level=1, assigned_version="light"),
            make_log(5, "done", pain_level=1, assigned_version="base"),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.light_days == 2
        assert eval_.growth_eligible is True


# ══════════════════════════════════════════════════════════════════════════════
# Условие 6: Recovery ≤ 1 дня
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoveryDaysLimit:

    def test_2_recovery_days_blocks_growth(self):
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, assigned_version="recovery"),
            make_log(3, "done", pain_level=1, assigned_version="recovery"),
            make_log(5, "done", pain_level=1, assigned_version="base"),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.recovery_days == 2
        assert eval_.growth_eligible is False

    def test_1_recovery_day_allows_growth(self):
        # День 1 — ключевой (base), день 3 — recovery (не ключевой)
        days = [
            make_day_plan(1, "run", is_key=True,  planned_minutes=50),
            make_day_plan(3, "run", is_key=False, planned_minutes=50),
            make_day_plan(5, "run", is_key=False, planned_minutes=50),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, assigned_version="base"),      # ключевая — выполнена
            make_log(3, "done", pain_level=1, assigned_version="recovery"),  # 1 recovery-день
            make_log(5, "done", pain_level=1, assigned_version="base"),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.recovery_days == 1
        assert eval_.growth_eligible is True


# ══════════════════════════════════════════════════════════════════════════════
# Условие 7: Не 3+ дней подряд без чек-ина
# ══════════════════════════════════════════════════════════════════════════════

class TestNoCheckinStreak:

    def test_3_days_no_checkin_blocks_growth(self):
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3, 4]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, checkin_done=False),
            make_log(2, "done", pain_level=1, checkin_done=False),
            make_log(3, "done", pain_level=1, checkin_done=False),
            make_log(4, "done", pain_level=1, checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False

    def test_rest_day_resets_no_checkin_streak(self):
        """День rest прерывает серию без чек-ина."""
        days = [
            make_day_plan(1, "run", is_key=True),
            make_day_plan(2, "rest"),
            make_day_plan(3, "run"),
            make_day_plan(4, "run"),
        ]
        week = make_week_plan(days)
        # Без чек-ина только дни 1 и 3 (день 2 — rest, прерывает)
        logs = [
            make_log(1, "done", pain_level=1, checkin_done=False),
            make_log(3, "done", pain_level=1, checkin_done=False),
            make_log(4, "done", pain_level=1, checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        # Максимальная серия без чек-ина = 1 (прервана rest), не блокирует
        assert eval_.growth_eligible is True


# ══════════════════════════════════════════════════════════════════════════════
# Recovery period: рост всегда блокирован
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoveryPeriod:

    def test_recovery_period_blocks_growth(self):
        """В recovery_period growth_eligible всегда False."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days, is_recovery_period=True)
        logs = [make_log(i, "done", pain_level=1) for i in [1, 3, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False
        assert eval_.no_growth_reason == "recovery_period"
        assert eval_.in_recovery_period is True

    def test_recovery_period_still_detects_rollback(self):
        """В recovery_period triggers_rollback всё равно работает."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3]]
        week = make_week_plan(days, period="recovery_period", is_recovery_period=True)
        logs = [make_log(i, "done", pain_level=3) for i in [1, 2, 3]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True
        assert eval_.growth_eligible is False  # всё равно False в recovery_period


# ══════════════════════════════════════════════════════════════════════════════
# actual_minutes — подсчёт беговых минут
# ══════════════════════════════════════════════════════════════════════════════

class TestActualMinutes:

    def test_done_run_counts_full(self):
        days = [
            make_day_plan(1, "run", is_key=True, planned_minutes=60),
            make_day_plan(3, "run", planned_minutes=50),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, assigned_version="base", planned_minutes=60),
            make_log(3, "done", pain_level=1, assigned_version="base", planned_minutes=50),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.actual_minutes == 110

    def test_light_run_counts_80_percent(self):
        """Light = planned × 0.80."""
        days = [make_day_plan(1, "run", is_key=True, planned_minutes=60)]
        week = make_week_plan(days)
        logs = [make_log(1, "done", pain_level=1, assigned_version="light", planned_minutes=60)]
        eval_ = evaluate_week(week, logs)
        assert eval_.actual_minutes == 48  # 60 × 0.80

    def test_recovery_version_not_counted(self):
        """Версия recovery не считается в actual_minutes."""
        days = [make_day_plan(1, "run", is_key=True, planned_minutes=60)]
        week = make_week_plan(days)
        logs = [make_log(1, "done", pain_level=1, assigned_version="recovery", planned_minutes=60)]
        eval_ = evaluate_week(week, logs)
        assert eval_.actual_minutes == 0

    def test_skipped_not_counted(self):
        days = [make_day_plan(1, "run", is_key=True, planned_minutes=60)]
        week = make_week_plan(days)
        logs = [make_log(1, "skipped", pain_level=1, assigned_version="base", planned_minutes=60)]
        eval_ = evaluate_week(week, logs)
        assert eval_.actual_minutes == 0

    def test_strength_not_counted_in_minutes(self):
        """Силовые не считаются в actual_minutes."""
        days = [
            make_day_plan(1, "strength", is_key=True, planned_minutes=40),
            make_day_plan(3, "run", planned_minutes=60),
        ]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", pain_level=1, assigned_version="base", planned_minutes=40),
            make_log(3, "done", pain_level=1, assigned_version="base", planned_minutes=60),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.actual_minutes == 60  # только run
