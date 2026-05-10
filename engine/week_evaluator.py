"""
engine/week_evaluator.py
Оценка недели и принятие решения по следующей неделе.
Spec разделы 3.9, 3.11.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.constants import (
    SUCCESS_THRESHOLD, MAX_LIGHT_DAYS_PER_WEEK, MAX_RECOVERY_DAYS_PER_WEEK,
    ROLLBACK_PAIN_DAYS, GROWTH_BLOCK_MILD_PAIN_DAYS,
    GROWTH_STREAK_FOR_RECOVERY, FAILSAFE_WEEKS_WITHOUT_RECOVERY,
    RECOVERY_MULTIPLIER, LIGHT_VOLUME_MULTIPLIER,
    get_growth_multiplier, get_level_ceiling, round_int,
)
from engine.red_flags import DayPainData, detect_high_pain_streak, detect_mild_pain_streak

if TYPE_CHECKING:
    from database.models import WeekPlan, SessionLog, User


# ══════════════════════════════════════════════════════════════════════════════
# Датаклассы результатов
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class WeekEvaluation:
    completion_rate: float        # 0.0-1.0 — доля выполненных тренировок
    keys_completed: bool          # все ли 3 ключевые засчитаны
    had_high_pain: bool           # хоть один день pain==3
    high_pain_streak: int         # макс серия дней с pain==3
    mild_pain_streak: int         # макс серия дней с pain==2
    light_days: int               # дней с версией Light
    recovery_days: int            # дней с версией Recovery
    actual_minutes: int           # выполненных беговых минут
    growth_eligible: bool         # можно ли расти
    no_growth_reason: str | None  # почему нельзя (если нельзя)
    triggers_rollback: bool       # 3 дня pain==3 подряд → red_flag
    in_recovery_period: bool = False  # неделя в составе recovery_period


@dataclass
class NextWeekDecision:
    next_target_minutes: int
    is_recovery_week: bool
    is_rollback: bool
    new_period: str | None        # если переходим в другой период
    cycle_ended: bool             # цикл завершён


# ══════════════════════════════════════════════════════════════════════════════
# evaluate_week
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_week(
    week_plan: "WeekPlan",
    logs: list["SessionLog"],
) -> WeekEvaluation:
    """
    Оценивает завершённую неделю по 7 критериям (spec 3.9.1).
    Детектор red_flag работает всегда, даже в recovery_period.
    """
    in_recovery = week_plan.is_recovery_period if hasattr(week_plan, "is_recovery_period") else (
        week_plan.period == "recovery_period"
    )

    # ── Индексируем логи по дню недели ───────────────────────────────────────
    log_by_day: dict[int, "SessionLog"] = {}
    for log in logs:
        if log.day_of_week:
            log_by_day[log.day_of_week] = log

    # ── Подсчёт completion_rate ───────────────────────────────────────────────
    planned_days = [d for d in week_plan.days if d.day_type != "rest"]
    n_planned = len(planned_days)

    done_count = 0
    for day_plan in planned_days:
        log = log_by_day.get(day_plan.day_of_week)
        if log and log.completion_status == "done":
            done_count += 1

    completion_rate = done_count / n_planned if n_planned > 0 else 0.0

    # ── Ключевые тренировки ───────────────────────────────────────────────────
    key_days = [d for d in week_plan.days if d.is_key]
    keys_completed = True
    for kd in key_days:
        completed = _is_key_completed(kd, log_by_day.get(kd.day_of_week))
        if not completed:
            keys_completed = False
            break

    # ── Pain анализ ───────────────────────────────────────────────────────────
    pain_data: list[DayPainData] = []
    for day_plan in sorted(week_plan.days, key=lambda d: d.day_of_week):
        if day_plan.day_type == "rest":
            continue
        log = log_by_day.get(day_plan.day_of_week)
        pain_val = log.pain_level if log and log.checkin_done else None
        pain_data.append(DayPainData(pain_level=pain_val))

    had_high_pain = any(d.pain_level == 3 for d in pain_data if d.pain_level is not None)
    triggers_rollback = detect_high_pain_streak(pain_data, days=ROLLBACK_PAIN_DAYS)

    # Серии боли
    high_streak = _count_streak(pain_data, target=3)
    mild_streak = _count_streak(pain_data, target=2)

    # ── Light / Recovery счётчики ─────────────────────────────────────────────
    light_days = 0
    recovery_days = 0
    for day_plan in week_plan.days:
        log = log_by_day.get(day_plan.day_of_week)
        if not log:
            continue
        if log.assigned_version == "light":
            light_days += 1
        elif log.assigned_version == "recovery":
            recovery_days += 1

    # ── Дни без чек-ина ───────────────────────────────────────────────────────
    no_checkin_streak = _max_no_checkin_streak(week_plan.days, log_by_day)

    # ── actual_running_minutes ────────────────────────────────────────────────
    actual_minutes = _calc_actual_minutes(week_plan.days, log_by_day)

    # ── Если в recovery_period: рост всегда отключён ─────────────────────────
    if in_recovery:
        return WeekEvaluation(
            completion_rate=completion_rate,
            keys_completed=keys_completed,
            had_high_pain=had_high_pain,
            high_pain_streak=high_streak,
            mild_pain_streak=mild_streak,
            light_days=light_days,
            recovery_days=recovery_days,
            actual_minutes=actual_minutes,
            growth_eligible=False,
            no_growth_reason="recovery_period",
            triggers_rollback=triggers_rollback,
            in_recovery_period=True,
        )

    # ── 7 условий успешной недели ─────────────────────────────────────────────
    no_growth_reason: str | None = None

    if completion_rate < SUCCESS_THRESHOLD:
        no_growth_reason = f"completion {completion_rate:.0%} < 85%"
    elif not keys_completed:
        no_growth_reason = "ключевые тренировки не выполнены"
    elif had_high_pain:
        no_growth_reason = "был день с болью (pain==3)"
    elif mild_streak >= GROWTH_BLOCK_MILD_PAIN_DAYS:
        no_growth_reason = f"pain==2 {mild_streak} дней подряд"
    elif light_days > MAX_LIGHT_DAYS_PER_WEEK:
        no_growth_reason = f"Light {light_days} дней > {MAX_LIGHT_DAYS_PER_WEEK}"
    elif recovery_days > MAX_RECOVERY_DAYS_PER_WEEK:
        no_growth_reason = f"Recovery {recovery_days} дней > {MAX_RECOVERY_DAYS_PER_WEEK}"
    elif no_checkin_streak >= 3:
        no_growth_reason = f"{no_checkin_streak} дней подряд без чек-ина"

    growth_eligible = no_growth_reason is None

    return WeekEvaluation(
        completion_rate=completion_rate,
        keys_completed=keys_completed,
        had_high_pain=had_high_pain,
        high_pain_streak=high_streak,
        mild_pain_streak=mild_streak,
        light_days=light_days,
        recovery_days=recovery_days,
        actual_minutes=actual_minutes,
        growth_eligible=growth_eligible,
        no_growth_reason=no_growth_reason,
        triggers_rollback=triggers_rollback,
        in_recovery_period=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# decide_next_week
# ══════════════════════════════════════════════════════════════════════════════

def decide_next_week(
    user: "User",
    current_week: "WeekPlan",
    evaluation: WeekEvaluation,
) -> NextWeekDecision:
    """
    По оценке текущей недели определяет параметры следующей.
    Обновляет счётчики user (growth_streak, weeks_since_recovery).
    """
    level = user.level or 1
    injury_return = getattr(user, "injury_return_active", False)
    period = current_week.period
    current_target = current_week.weekly_target_minutes
    ceiling = get_level_ceiling(level, injury_return)
    peak = getattr(user, "peak_volume_minutes", None) or current_target

    # ── В recovery_period: удерживаем объём на месте ─────────────────────────
    if evaluation.in_recovery_period:
        mac_peak = getattr(user, "macrocycle_peak_volume", None) or peak
        target = round_int(mac_peak * RECOVERY_MULTIPLIER)
        target = min(target, ceiling)
        return NextWeekDecision(
            next_target_minutes=target,
            is_recovery_week=False,
            is_rollback=False,
            new_period=None,
            cycle_ended=False,
        )

    # ── Red flag активен → откат ──────────────────────────────────────────────
    if getattr(user, "red_flag_active", False):
        last_vol = getattr(user, "last_successful_volume", None)
        if not last_vol:
            from engine.constants import get_level_start_volume
            last_vol = get_level_start_volume(level, user.entry_point or "base", injury_return)
        return NextWeekDecision(
            next_target_minutes=last_vol,
            is_recovery_week=False,
            is_rollback=True,
            new_period=None,
            cycle_ended=False,
        )

    # ── Проверяем weekly unload ───────────────────────────────────────────────
    growth_streak = getattr(user, "growth_streak", 0)
    weeks_since_recovery = getattr(user, "weeks_since_recovery", 0)

    unload_needed = (
        growth_streak >= GROWTH_STREAK_FOR_RECOVERY
        or weeks_since_recovery >= FAILSAFE_WEEKS_WITHOUT_RECOVERY
    )

    if unload_needed and evaluation.growth_eligible:
        # Разгрузочная неделя
        target = round_int(peak * RECOVERY_MULTIPLIER)
        target = min(target, ceiling)
        return NextWeekDecision(
            next_target_minutes=target,
            is_recovery_week=True,
            is_rollback=False,
            new_period=None,
            cycle_ended=False,
        )

    # ── Прогрессия или удержание ──────────────────────────────────────────────
    if current_week.is_recovery_week:
        # После разгрузочной: возврат к пику × growth_mult
        growth_mult = get_growth_multiplier(level, period, injury_return)
        target = round_int(peak * growth_mult)
    elif evaluation.growth_eligible:
        growth_mult = get_growth_multiplier(level, period, injury_return)
        target = round_int(evaluation.actual_minutes * growth_mult)
    else:
        # Удержание плана
        target = current_target

    target = min(target, ceiling)

    return NextWeekDecision(
        next_target_minutes=target,
        is_recovery_week=False,
        is_rollback=False,
        new_period=None,
        cycle_ended=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ══════════════════════════════════════════════════════════════════════════════

def _is_key_completed(day_plan, log: "SessionLog | None") -> bool:
    """Засчитана ли ключевая тренировка (spec 3.8.2)."""
    if not day_plan.is_key:
        return False
    if not log or log.completion_status != "done":
        return False
    if log.assigned_version == "recovery":
        return False  # Recovery в ключевой → не засчитан
    return True


def _count_streak(pain_data: list[DayPainData], target: int) -> int:
    """Максимальная непрерывная серия дней с pain == target."""
    max_streak = 0
    current = 0
    for d in pain_data:
        if d.pain_level == target:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _max_no_checkin_streak(day_plans, log_by_day: dict) -> int:
    """Максимальная непрерывная серия дней без чек-ина."""
    max_streak = 0
    current = 0
    for dp in sorted(day_plans, key=lambda d: d.day_of_week):
        if dp.day_type == "rest":
            current = 0
            continue
        log = log_by_day.get(dp.day_of_week)
        if not log or not log.checkin_done:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _calc_actual_minutes(day_plans, log_by_day: dict) -> int:
    """
    Фактические беговые минуты за неделю (spec 3.9.3).
    Считаем только run-дни с completion_status==done, не recovery-версии.
    Light = planned × 0.80.
    """
    total = 0
    for dp in day_plans:
        if dp.day_type != "run":
            continue
        log = log_by_day.get(dp.day_of_week)
        if not log or log.completion_status != "done":
            continue
        if log.assigned_version == "recovery":
            continue

        planned = log.planned_minutes or dp.planned_minutes or 0
        if log.assigned_version == "light":
            total += round_int(planned * LIGHT_VOLUME_MULTIPLIER)
        else:
            total += planned

    return total
