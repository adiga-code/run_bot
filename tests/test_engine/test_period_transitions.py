"""
tests/test_engine/test_period_transitions.py

Тесты engine/period_transitions.py (spec раздел 3.4).
  - check_period_transition: L1 base_in→base, base→specialized
  - check_period_transition: L2/L3 base→preparatory
  - check_period_transition: условия мин. недель и avg completion
  - check_cycle_end: конец цикла по max weeks
  - start_new_cycle: advance / stay / redo
  - check_l1_long_stage_transition: стадия 1→2
  - check_injury_return_exit: выход из return-mode
"""
import pytest
from types import SimpleNamespace
from engine.period_transitions import (
    check_period_transition,
    check_cycle_end,
    start_new_cycle,
    check_l1_long_stage_transition,
    check_injury_return_exit,
    should_apply_weekly_unload,
)
from engine.week_evaluator import WeekEvaluation
from engine.constants import (
    L1_CYCLE_MAX_WEEKS, L2_CYCLE_MAX_WEEKS,
    L3_REGULAR_CYCLE_MAX_WEEKS, L3_RETURN_CYCLE_MAX_WEEKS,
    L1_CEILING, L2_CEILING, L3_REGULAR_CEILING, L3_RETURN_CEILING,
    L1_START_VOLUME_BASE_IN, L1_START_VOLUME_BASE, L2_START_VOLUME,
    L3_REGULAR_START_VOLUME, L3_RETURN_START_VOLUME,
)


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_user(
    level: int = 1,
    current_period: str = "base",
    period_week_number: int = 1,
    program_week_number: int = 1,
    injury_return_active: bool = False,
    has_goal_race: bool = False,
    q_continuous_run_test: str | None = "yes",
    l1_long_independent: bool = False,
    growth_streak: int = 0,
    weeks_since_recovery: int = 0,
    weekly_target_minutes: int = 200,
    macrocycle_peak_volume: int | None = None,
    entry_point: str = "base",
    cycle_number: int = 1,
    red_flag_active: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        level=level,
        current_period=current_period,
        period_week_number=period_week_number,
        program_week_number=program_week_number,
        injury_return_active=injury_return_active,
        has_goal_race=has_goal_race,
        q_continuous_run_test=q_continuous_run_test,
        l1_long_independent=l1_long_independent,
        growth_streak=growth_streak,
        weeks_since_recovery=weeks_since_recovery,
        weekly_target_minutes=weekly_target_minutes,
        macrocycle_peak_volume=macrocycle_peak_volume,
        peak_volume_minutes=weekly_target_minutes,
        entry_point=entry_point,
        cycle_number=cycle_number,
        red_flag_active=red_flag_active,
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


def bad_eval() -> WeekEvaluation:
    return WeekEvaluation(
        completion_rate=0.7,
        keys_completed=False,
        had_high_pain=False,
        high_pain_streak=0,
        mild_pain_streak=0,
        light_days=0,
        recovery_days=0,
        actual_minutes=140,
        growth_eligible=False,
        no_growth_reason="completion 70% < 85%",
        triggers_rollback=False,
        in_recovery_period=False,
    )


def pain_eval() -> WeekEvaluation:
    return WeekEvaluation(
        completion_rate=1.0,
        keys_completed=True,
        had_high_pain=True,
        high_pain_streak=1,
        mild_pain_streak=0,
        light_days=0,
        recovery_days=0,
        actual_minutes=200,
        growth_eligible=False,
        no_growth_reason="был день с болью (pain==3)",
        triggers_rollback=False,
        in_recovery_period=False,
    )


def evals_good(n: int = 6) -> list[WeekEvaluation]:
    return [good_eval() for _ in range(n)]


def evals_with_pain() -> list[WeekEvaluation]:
    evals = evals_good(4)
    evals[-1] = pain_eval()
    return evals


def recent_weeks_placeholder(n: int = 0) -> list:
    return [SimpleNamespace() for _ in range(n)]


# ══════════════════════════════════════════════════════════════════════════════
# L1 base_in → base
# ══════════════════════════════════════════════════════════════════════════════

class TestL1BaseInToBase:

    def test_min_weeks_not_met(self):
        """Меньше 4 недель в base_in → нет перехода."""
        user = make_user(level=1, current_period="base_in", period_week_number=3)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(3))
        assert result is None

    def test_enough_weeks_can_run_20_no_pain(self):
        """4+ нед, может бежать 20 мин, ≥85%, нет боли → переход."""
        user = make_user(
            level=1, current_period="base_in", period_week_number=4,
            q_continuous_run_test="yes",
        )
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(4))
        assert result == "base"

    def test_cannot_run_20_no_transition(self):
        """Не может бежать 20 мин → нет перехода."""
        user = make_user(
            level=1, current_period="base_in", period_week_number=4,
            q_continuous_run_test="no",
        )
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(4))
        assert result is None

    def test_pain_blocks_transition(self):
        """Боль в последние 2 нед → нет перехода."""
        user = make_user(
            level=1, current_period="base_in", period_week_number=4,
            q_continuous_run_test="yes",
        )
        result = check_period_transition(user, recent_weeks_placeholder(), evals_with_pain())
        assert result is None

    def test_low_completion_blocks_transition(self):
        """Completion < 85% → нет перехода."""
        user = make_user(
            level=1, current_period="base_in", period_week_number=4,
            q_continuous_run_test="yes",
        )
        evals = [bad_eval()] * 4
        result = check_period_transition(user, recent_weeks_placeholder(), evals)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# L1 base → specialized
# ══════════════════════════════════════════════════════════════════════════════

class TestL1BaseToSpecialized:

    def test_no_goal_race_no_transition(self):
        """Нет цели → остаётся в base навсегда."""
        user = make_user(level=1, current_period="base", period_week_number=8, has_goal_race=False)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(8))
        assert result is None

    def test_with_goal_race_transition(self):
        """Есть цель, 6+ нед, ≥85%, нет боли → specialized."""
        user = make_user(level=1, current_period="base", period_week_number=6, has_goal_race=True)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(6))
        assert result == "specialized"

    def test_min_weeks_not_met_no_transition(self):
        user = make_user(level=1, current_period="base", period_week_number=5, has_goal_race=True)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(5))
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# L2 base → preparatory
# ══════════════════════════════════════════════════════════════════════════════

class TestL2BaseToPreparatory:

    def test_l2_base_to_prep(self):
        """L2: 6+ нед, ≥85%, нет боли → preparatory."""
        user = make_user(level=2, current_period="base", period_week_number=6)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(6))
        assert result == "preparatory"

    def test_l2_too_few_weeks(self):
        user = make_user(level=2, current_period="base", period_week_number=5)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(5))
        assert result is None

    def test_l2_pain_blocks(self):
        user = make_user(level=2, current_period="base", period_week_number=6)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_with_pain())
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# L3 regular base → preparatory
# ══════════════════════════════════════════════════════════════════════════════

class TestL3RegularBaseToPreparatory:

    def test_l3_regular_base_to_prep(self):
        user = make_user(level=3, injury_return_active=False, current_period="base", period_week_number=6)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(6))
        assert result == "preparatory"

    def test_l3_regular_too_few_weeks(self):
        user = make_user(level=3, injury_return_active=False, current_period="base", period_week_number=5)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(5))
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# L3 after break (injury_return) — base → preparatory как L2
# ══════════════════════════════════════════════════════════════════════════════

class TestL3ReturnBaseToPreparatory:

    def test_l3_return_base_to_prep(self):
        """L3 after break: 6+ нед → preparatory."""
        user = make_user(level=3, injury_return_active=True, current_period="base", period_week_number=6)
        result = check_period_transition(user, recent_weeks_placeholder(), evals_good(6))
        assert result == "preparatory"


# ══════════════════════════════════════════════════════════════════════════════
# check_cycle_end
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckCycleEnd:

    def make_eval_in_recovery(self) -> WeekEvaluation:
        e = good_eval()
        e = WeekEvaluation(
            completion_rate=e.completion_rate,
            keys_completed=e.keys_completed,
            had_high_pain=e.had_high_pain,
            high_pain_streak=e.high_pain_streak,
            mild_pain_streak=e.mild_pain_streak,
            light_days=e.light_days,
            recovery_days=e.recovery_days,
            actual_minutes=e.actual_minutes,
            growth_eligible=False,
            no_growth_reason="recovery_period",
            triggers_rollback=False,
            in_recovery_period=True,
        )
        return e

    def test_max_weeks_l1_triggers_end(self):
        """cycle_weeks >= max → цикл завершён."""
        user = make_user(level=1, current_period="base", program_week_number=L1_CYCLE_MAX_WEEKS)
        eval_ = good_eval()
        assert check_cycle_end(user, eval_) is True

    def test_max_weeks_l2_triggers_end(self):
        user = make_user(level=2, current_period="preparatory", program_week_number=L2_CYCLE_MAX_WEEKS)
        eval_ = good_eval()
        assert check_cycle_end(user, eval_) is True

    def test_max_weeks_l3_regular(self):
        user = make_user(level=3, injury_return_active=False, current_period="base",
                         program_week_number=L3_REGULAR_CYCLE_MAX_WEEKS)
        eval_ = good_eval()
        assert check_cycle_end(user, eval_) is True

    def test_max_weeks_l3_return(self):
        user = make_user(level=3, injury_return_active=True, current_period="base",
                         program_week_number=L3_RETURN_CYCLE_MAX_WEEKS)
        eval_ = good_eval()
        assert check_cycle_end(user, eval_) is True

    def test_not_at_max_weeks_no_end(self):
        """Меньше max недель → цикл не завершён (при условии что не в recovery_period)."""
        user = make_user(level=2, current_period="base", program_week_number=10)
        eval_ = good_eval()
        assert check_cycle_end(user, eval_) is False

    def test_l1_recovery_period_min_weeks_triggers_end(self):
        """L1: в recovery_period после минимума недель → цикл завершён."""
        user = make_user(level=1, current_period="recovery_period",
                         period_week_number=2, program_week_number=15)
        eval_ = self.make_eval_in_recovery()
        assert check_cycle_end(user, eval_) is True


# ══════════════════════════════════════════════════════════════════════════════
# start_new_cycle
# ══════════════════════════════════════════════════════════════════════════════

class TestStartNewCycle:

    def test_advance_l1_to_l2(self):
        """advance: level=1 → level=2."""
        user = make_user(level=1, cycle_number=1, weekly_target_minutes=200,
                         macrocycle_peak_volume=220, entry_point="base")
        result = start_new_cycle(user, mode="advance")
        assert result["level"] == 2
        assert result["cycle_number"] == 2
        assert result["program_week_number"] == 1
        assert result["period_week_number"] == 1
        assert result["growth_streak"] == 0

    def test_advance_l2_to_l3(self):
        user = make_user(level=2, cycle_number=2, weekly_target_minutes=280,
                         macrocycle_peak_volume=280)
        result = start_new_cycle(user, mode="advance")
        assert result["level"] == 3

    def test_advance_l3_stays_at_l3(self):
        """Максимальный уровень 3 — не увеличивается выше."""
        user = make_user(level=3, cycle_number=3, weekly_target_minutes=400,
                         macrocycle_peak_volume=400)
        result = start_new_cycle(user, mode="advance")
        assert result["level"] == 3

    def test_stay_mode(self):
        """stay: тот же уровень, peak × 1.4."""
        user = make_user(level=2, cycle_number=1, weekly_target_minutes=200,
                         macrocycle_peak_volume=200)
        result = start_new_cycle(user, mode="stay")
        assert result["level"] == 2
        # 200 × 1.4 = 280, но не выше ceiling L2=300
        assert result["weekly_target_minutes"] == pytest.approx(280, abs=2)
        assert result["weekly_target_minutes"] <= L2_CEILING

    def test_redo_mode(self):
        """redo: тот же уровень, peak × 0.6."""
        user = make_user(level=2, cycle_number=1, weekly_target_minutes=200,
                         macrocycle_peak_volume=200)
        result = start_new_cycle(user, mode="redo")
        assert result["level"] == 2
        # 200 × 0.6 = 120
        assert result["weekly_target_minutes"] == pytest.approx(120, abs=2)

    def test_new_cycle_resets_counters(self):
        """Новый цикл сбрасывает growth_streak и weeks_since_recovery."""
        user = make_user(level=1, cycle_number=1, growth_streak=5,
                         weeks_since_recovery=6, weekly_target_minutes=180,
                         macrocycle_peak_volume=180, entry_point="base_in")
        result = start_new_cycle(user, mode="stay")
        assert result["growth_streak"] == 0
        assert result["weeks_since_recovery"] == 0
        assert result["macrocycle_peak_volume"] is None

    def test_stay_respects_ceiling(self):
        """stay: peak × 1.4 не превышает ceiling уровня."""
        user = make_user(level=1, cycle_number=1, weekly_target_minutes=200,
                         macrocycle_peak_volume=200)
        result = start_new_cycle(user, mode="stay")
        assert result["weekly_target_minutes"] <= L1_CEILING


# ══════════════════════════════════════════════════════════════════════════════
# check_l1_long_stage_transition (стадия 1 → 2)
# ══════════════════════════════════════════════════════════════════════════════

class TestL1LongStageTransition:

    def test_already_independent_no_transition(self):
        """Если уже в стадии 2 → False."""
        user = make_user(level=1, l1_long_independent=True)
        result = check_l1_long_stage_transition(user, evals_good(3), easy_minutes_last_week=50)
        assert result is False

    def test_not_enough_weeks_no_transition(self):
        """Меньше 2 недель без боли → False."""
        user = make_user(level=1, l1_long_independent=False)
        result = check_l1_long_stage_transition(user, evals_good(1), easy_minutes_last_week=50)
        assert result is False

    def test_easy_threshold_not_met(self):
        """Easy < 40 мин → не переходим."""
        user = make_user(level=1, l1_long_independent=False)
        evals = evals_good(2)
        result = check_l1_long_stage_transition(user, evals, easy_minutes_last_week=35)
        assert result is False

    def test_all_conditions_met(self):
        """2 нед без боли + easy ≥ 40 мин → переход в стадию 2."""
        user = make_user(level=1, l1_long_independent=False)
        evals = evals_good(3)
        result = check_l1_long_stage_transition(user, evals, easy_minutes_last_week=40)
        assert result is True

    def test_pain_in_recent_weeks_blocks(self):
        """Боль в последние 2 нед → не переходим."""
        user = make_user(level=1, l1_long_independent=False)
        evals = evals_good(3)
        evals[-1] = pain_eval()
        result = check_l1_long_stage_transition(user, evals, easy_minutes_last_week=50)
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# check_injury_return_exit
# ══════════════════════════════════════════════════════════════════════════════

class TestInjuryReturnExit:

    def test_not_in_return_mode(self):
        """Не в return-mode → False."""
        user = make_user(level=2, injury_return_active=False)
        result = check_injury_return_exit(user, evals_good(4))
        assert result is False

    def test_l2_return_not_enough_weeks(self):
        """L2 return: нужно минимум 4 успешных нед."""
        user = make_user(level=2, injury_return_active=True, weekly_target_minutes=150)
        result = check_injury_return_exit(user, evals_good(3))
        assert result is False

    def test_l2_return_volume_not_reached(self):
        """L2 return: объём ещё не вышел на 150 мин/нед → нет выхода."""
        user = make_user(level=2, injury_return_active=True, weekly_target_minutes=120)
        result = check_injury_return_exit(user, evals_good(4))
        assert result is False

    def test_l2_return_exit_success(self):
        """L2 return: 4 нед успешных + объём ≥ 150 → выход."""
        user = make_user(level=2, injury_return_active=True, weekly_target_minutes=150)
        result = check_injury_return_exit(user, evals_good(4))
        assert result is True

    def test_l3_return_exit_success(self):
        """L3 return: 4 нед + объём ≥ 240 → выход."""
        user = make_user(level=3, injury_return_active=True, weekly_target_minutes=240)
        result = check_injury_return_exit(user, evals_good(4))
        assert result is True

    def test_pain_blocks_exit(self):
        """Боль в последние 2 нед → нет выхода."""
        user = make_user(level=2, injury_return_active=True, weekly_target_minutes=150)
        evals = evals_good(6)
        evals[-1] = pain_eval()
        result = check_injury_return_exit(user, evals)
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# should_apply_weekly_unload
# ══════════════════════════════════════════════════════════════════════════════

class TestShouldApplyWeeklyUnload:

    def test_no_unload_if_close_to_recovery_period(self):
        """Если до recovery_period ≤ 2 недели → не разгружаем."""
        user = make_user(level=2, growth_streak=5, weeks_since_recovery=10)
        result = should_apply_weekly_unload(user, weeks_until_recovery_period=2)
        assert result is False

    def test_unload_if_growth_streak_3(self):
        user = make_user(level=2, growth_streak=3, weeks_since_recovery=0)
        result = should_apply_weekly_unload(user, weeks_until_recovery_period=10)
        assert result is True

    def test_unload_failsafe_6_weeks(self):
        user = make_user(level=2, growth_streak=0, weeks_since_recovery=6)
        result = should_apply_weekly_unload(user, weeks_until_recovery_period=10)
        assert result is True

    def test_no_unload_below_thresholds(self):
        user = make_user(level=2, growth_streak=2, weeks_since_recovery=5)
        result = should_apply_weekly_unload(user, weeks_until_recovery_period=10)
        assert result is False
