"""
tests/test_engine/test_no_checkin_days.py

Тесты поведения при отсутствующих чек-инах (spec раздел 3.9.1, условие 7).
  - Дни без чек-ина не засчитываются в completion_rate
  - 3+ дней подряд без чек-ина → growth blocked
  - День rest прерывает серию без чек-ина
  - NULL pain_level (нет чек-ина) сбрасывает pain streak
  - Неполная неделя (несколько логов отсутствует) обрабатывается корректно
"""
import pytest
from types import SimpleNamespace
from engine.week_evaluator import evaluate_week, WeekEvaluation


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_day_plan(dow: int, day_type: str = "run", is_key: bool = False,
                  planned_minutes: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=dow, day_type=day_type,
        is_key=is_key, planned_minutes=planned_minutes,
    )


def make_week_plan(days, period: str = "base") -> SimpleNamespace:
    return SimpleNamespace(
        days=days, period=period,
        is_recovery_period=False,
        weekly_target_minutes=200,
        is_recovery_week=False,
    )


def make_log(dow: int, status: str = "done", pain: int = 1,
             checkin_done: bool = True, version: str = "base") -> SimpleNamespace:
    return SimpleNamespace(
        day_of_week=dow, completion_status=status,
        pain_level=pain, checkin_done=checkin_done,
        assigned_version=version, planned_minutes=50,
    )


# ══════════════════════════════════════════════════════════════════════════════
# completion_rate при отсутствии чек-ина
# ══════════════════════════════════════════════════════════════════════════════

class TestCompletionWithMissingLogs:

    def test_missing_log_counts_as_0(self):
        """Отсутствующий лог = не выполнено (0)."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 3, 5]]
        week = make_week_plan(days)
        # Лог только для дня 1
        logs = [make_log(1, "done")]
        eval_ = evaluate_week(week, logs)
        # 1/3 = 0.33
        assert eval_.completion_rate == pytest.approx(1 / 3, abs=0.01)

    def test_no_logs_zero_completion(self):
        """Нет логов вообще → completion=0."""
        days = [make_day_plan(i, "run") for i in [1, 3, 5]]
        week = make_week_plan(days)
        eval_ = evaluate_week(week, [])
        assert eval_.completion_rate == pytest.approx(0.0)
        assert eval_.growth_eligible is False

    def test_rest_day_not_in_denominator(self):
        """Rest-дни не входят в знаменатель completion_rate."""
        days = [
            make_day_plan(1, "run", is_key=True),
            make_day_plan(2, "rest"),
            make_day_plan(3, "run"),
        ]
        week = make_week_plan(days)
        logs = [make_log(1, "done"), make_log(3, "done")]
        eval_ = evaluate_week(week, logs)
        assert eval_.completion_rate == pytest.approx(1.0)


# ══════════════════════════════════════════════════════════════════════════════
# Серия без чек-ина → блок роста
# ══════════════════════════════════════════════════════════════════════════════

class TestNoCheckinStreak:

    def test_3_days_no_checkin_blocks_growth(self):
        """3+ дней подряд без чек-ина (во всех активных днях) → growth blocked."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3, 5]]
        week = make_week_plan(days)
        # Дни 1, 2, 3 — без чек-ина (done, но checkin_done=False)
        logs = [
            make_log(1, "done", checkin_done=False),
            make_log(2, "done", checkin_done=False),
            make_log(3, "done", checkin_done=False),
            make_log(5, "done", checkin_done=True),  # 4-й день — с чек-ином
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is False

    def test_2_days_no_checkin_ok(self):
        """2 дня без чек-ина — не блокирует."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", checkin_done=False),
            make_log(2, "done", checkin_done=False),
            make_log(3, "done", checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.growth_eligible is True

    def test_rest_day_breaks_no_checkin_streak(self):
        """Rest-день прерывает серию без чек-ина."""
        days = [
            make_day_plan(1, "run", is_key=True),
            make_day_plan(2, "rest"),           # прерывает серию
            make_day_plan(3, "run"),
            make_day_plan(4, "run"),
            make_day_plan(5, "run"),
        ]
        week = make_week_plan(days)
        # Дни 1, 3, 4 — без чек-ина, но между 1 и 3 есть rest-день
        logs = [
            make_log(1, "done", checkin_done=False),
            make_log(3, "done", checkin_done=False),
            make_log(4, "done", checkin_done=False),
            make_log(5, "done", checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        # Макс серия: {3,4} = 2 (до rest прервалась), не достигает 3
        assert eval_.growth_eligible is True


# ══════════════════════════════════════════════════════════════════════════════
# NULL pain_level сбрасывает pain streak
# ══════════════════════════════════════════════════════════════════════════════

class TestNullPainResetsStreak:

    def test_null_checkin_resets_pain3_streak(self):
        """Отсутствие чек-ина обнуляет серию pain==3 для triggers_rollback."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3, 4, 5]]
        week = make_week_plan(days)
        # pain==3 на дни 1,2; нет чек-ина на 3; pain==3 на дни 4,5
        logs = [
            make_log(1, "done", pain=3, checkin_done=True),
            make_log(2, "done", pain=3, checkin_done=True),
            make_log(3, "done", pain=1, checkin_done=False),  # нет чек-ина
            make_log(4, "done", pain=3, checkin_done=True),
            make_log(5, "done", pain=3, checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        # Серии: [3,3,None,3,3] — максимальная серия из 2 (не 3)
        assert eval_.triggers_rollback is False

    def test_5_consecutive_pain3_triggers(self):
        """5 дней подряд pain==3 → rollback."""
        days = [make_day_plan(i, "run") for i in [1, 2, 3, 4, 5]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", pain=3, checkin_done=True) for i in [1, 2, 3, 4, 5]]
        eval_ = evaluate_week(week, logs)
        assert eval_.triggers_rollback is True


# ══════════════════════════════════════════════════════════════════════════════
# Смешанные сценарии
# ══════════════════════════════════════════════════════════════════════════════

class TestMixedScenarios:

    def test_skipped_but_checkin_done_counts_as_done_for_checkin_streak(self):
        """Лог с checkin_done=True даже при skipped — чек-ин засчитан."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3, 4]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done", checkin_done=False),
            make_log(2, "done", checkin_done=False),
            make_log(3, "skipped", checkin_done=True),   # чек-ин есть
            make_log(4, "done", checkin_done=True),
        ]
        eval_ = evaluate_week(week, logs)
        # Серия без чек-ина = {1,2} = 2 < 3 → не блокирует
        assert eval_.growth_eligible is not False or "checkin" not in (eval_.no_growth_reason or "")

    def test_all_checkin_done_false_blocks(self):
        """Все дни без чек-ина → completion=0 и no_checkin_streak ≥ 3."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3, 4]]
        week = make_week_plan(days)
        logs = [make_log(i, "done", checkin_done=False) for i in [1, 2, 3, 4]]
        eval_ = evaluate_week(week, logs)
        # Нет чек-ина ни в одном дне → серия = 4 → блок роста
        assert eval_.growth_eligible is False

    def test_partial_week_2_of_4_done(self):
        """2/4 тренировок выполнены (50% < 85%) → не eligible."""
        days = [make_day_plan(i, "run", is_key=(i == 1)) for i in [1, 2, 3, 4]]
        week = make_week_plan(days)
        logs = [
            make_log(1, "done"),
            make_log(2, "done"),
            make_log(3, "skipped"),
            make_log(4, "skipped"),
        ]
        eval_ = evaluate_week(week, logs)
        assert eval_.completion_rate == pytest.approx(0.5)
        assert eval_.growth_eligible is False
