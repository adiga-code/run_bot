"""
engine/period_transitions.py
Переходы между периодами и уровнями.
Spec разделы 3.4, 3.4.5а.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from engine.constants import (
    SUCCESS_THRESHOLD,
    L1_PERIOD_MIN_WEEKS, L2_PERIOD_MIN_WEEKS, L3_REGULAR_PERIOD_MIN_WEEKS,
    L1_CYCLE_MAX_WEEKS, L2_CYCLE_MAX_WEEKS,
    L3_REGULAR_CYCLE_MAX_WEEKS, L3_RETURN_CYCLE_MAX_WEEKS,
    L3_RETURN_EXIT_SUCCESS_WEEKS_MIN, L3_RETURN_EXIT_VOLUME_TARGET,
    L2_RETURN_EXIT_SUCCESS_WEEKS_MIN, L2_RETURN_EXIT_VOLUME_TARGET,
    L1_LONG_STAGE2_NO_PAIN_WEEKS, L1_LONG_STAGE2_EASY_THRESHOLD,
    GROWTH_STREAK_FOR_RECOVERY, FAILSAFE_WEEKS_WITHOUT_RECOVERY,
    compute_recovery_period_weeks,
    get_level_start_volume, get_level_ceiling,
    CYCLE_END_STAY_VOLUME_MULTIPLIER, CYCLE_END_REDO_VOLUME_MULTIPLIER,
    round_int,
)

if TYPE_CHECKING:
    from database.models import User, WeekPlan
    from engine.week_evaluator import WeekEvaluation


# ══════════════════════════════════════════════════════════════════════════════
# should_apply_weekly_unload
# ══════════════════════════════════════════════════════════════════════════════

def should_apply_weekly_unload(user: "User", weeks_until_recovery_period: int) -> bool:
    """
    Нужна ли разгрузочная неделя прямо сейчас?

    Recovery_period имеет приоритет: если до него ≤ 2 недели —
    пропускаем weekly unload во избежание двойной разгрузки.
    """
    if weeks_until_recovery_period <= 2:
        return False
    growth_streak = getattr(user, "growth_streak", 0)
    weeks_since = getattr(user, "weeks_since_recovery", 0)
    return growth_streak >= GROWTH_STREAK_FOR_RECOVERY or weeks_since >= FAILSAFE_WEEKS_WITHOUT_RECOVERY


def calc_weeks_until_recovery_period(user: "User") -> int:
    """
    Считает сколько недель осталось до начала recovery_period
    на основе текущего периода, period_week_number и минимальной длины периода.
    """
    level = user.level or 1
    injury_return = getattr(user, "injury_return_active", False)
    period = user.current_period or "base"
    pw_num = user.period_week_number or 1

    # recovery_period бывает только у L1 и L3 regular
    if level == 2 or (level == 3 and injury_return):
        return 99  # нет multi-week recovery period

    # Определяем порядок периодов
    if level == 1:
        sequence = ["base_in", "base", "specialized", "recovery_period"]
        min_weeks = L1_PERIOD_MIN_WEEKS
    else:  # L3 regular
        sequence = ["base", "preparatory", "recovery_period"]
        min_weeks = L3_REGULAR_PERIOD_MIN_WEEKS

    # Если уже в recovery_period или после него
    if period == "recovery_period" or period not in sequence:
        return 0

    idx = sequence.index(period)
    # Оставшиеся недели в текущем периоде
    remaining_current = max(0, min_weeks.get(period, 6) - pw_num)
    # Суммируем минимальные недели следующих периодов до recovery_period
    total = remaining_current
    for next_p in sequence[idx + 1:]:
        if next_p == "recovery_period":
            break
        total += min_weeks.get(next_p, 6)
    return total


# ══════════════════════════════════════════════════════════════════════════════
# check_period_transition
# ══════════════════════════════════════════════════════════════════════════════

def check_period_transition(
    user: "User",
    recent_weeks: list["WeekPlan"],
    recent_evals: list["WeekEvaluation"],
) -> str | None:
    """
    Возвращает название нового периода или None.
    Проверяет условия перехода (spec 3.4.2).
    """
    level = user.level or 1
    injury_return = getattr(user, "injury_return_active", False)
    period = user.current_period or "base"
    pw_num = user.period_week_number or 1

    if not recent_evals:
        return None

    # Общие условия для большинства переходов
    last_eval = recent_evals[-1]
    all_success = all(e.growth_eligible for e in recent_evals[-4:]) if recent_evals else False
    no_pain = not any(e.had_high_pain for e in recent_evals[-2:])

    # ── L1 base_in → base ────────────────────────────────────────────────────
    if level == 1 and period == "base_in":
        min_weeks = L1_PERIOD_MIN_WEEKS["base_in"]
        if pw_num < min_weeks:
            return None
        # Условие: может бежать 20+ мин, ≥85% выполнения, нет боли
        can_run_20 = _can_run_20_min(user)
        avg_completion = _avg_completion(recent_evals[-min_weeks:])
        if can_run_20 and avg_completion >= SUCCESS_THRESHOLD and no_pain:
            return "base"
        return None

    # ── L1 base → specialized ─────────────────────────────────────────────────
    if level == 1 and period == "base":
        min_weeks = L1_PERIOD_MIN_WEEKS["base"]
        if pw_num < min_weeks:
            return None
        if not getattr(user, "has_goal_race", False):
            return None  # нет цели → остаётся в base
        avg_completion = _avg_completion(recent_evals[-min_weeks:])
        if avg_completion >= SUCCESS_THRESHOLD and no_pain:
            return "specialized"
        return None

    # ── L1 specialized → recovery_period ─────────────────────────────────────
    if level == 1 and period == "specialized":
        min_weeks = L1_PERIOD_MIN_WEEKS["specialized"]
        if pw_num < min_weeks:
            return None
        # После пика объёма — автоматически
        if last_eval.growth_eligible is False and not last_eval.had_high_pain:
            return "recovery_period"
        return None

    # ── L2 base → preparatory ─────────────────────────────────────────────────
    if level == 2 and period == "base":
        min_weeks = L2_PERIOD_MIN_WEEKS["base"]
        if pw_num < min_weeks:
            return None
        avg_completion = _avg_completion(recent_evals[-min_weeks:])
        if avg_completion >= SUCCESS_THRESHOLD and no_pain:
            return "preparatory"
        return None

    # ── L3 regular base → preparatory ────────────────────────────────────────
    if level == 3 and not injury_return and period == "base":
        min_weeks = L3_REGULAR_PERIOD_MIN_WEEKS["base"]
        if pw_num < min_weeks:
            return None
        avg_completion = _avg_completion(recent_evals[-min_weeks:])
        if avg_completion >= SUCCESS_THRESHOLD and no_pain:
            return "preparatory"
        return None

    # ── L3 after break: base → preparatory (как L2) ───────────────────────────
    if level == 3 and injury_return and period == "base":
        min_weeks = L2_PERIOD_MIN_WEEKS["base"]
        if pw_num < min_weeks:
            return None
        avg_completion = _avg_completion(recent_evals[-min_weeks:])
        if avg_completion >= SUCCESS_THRESHOLD and no_pain:
            return "preparatory"
        return None

    return None


# ══════════════════════════════════════════════════════════════════════════════
# check_cycle_end
# ══════════════════════════════════════════════════════════════════════════════

def check_cycle_end(user: "User", evaluation: "WeekEvaluation") -> bool:
    """
    Цикл завершён?
    Конец цикла наступает после финальной разгрузочной/recovery_period недели.
    """
    level = user.level or 1
    injury_return = getattr(user, "injury_return_active", False)
    period = user.current_period or "base"
    pw_num = user.period_week_number or 1
    cycle_weeks = user.program_week_number or 1

    # Максимум цикла — принудительное завершение
    max_weeks = _get_cycle_max_weeks(level, injury_return)
    if cycle_weeks >= max_weeks:
        return True

    # L2 / L3 after break: одна разгрузочная неделя в конце preparatory
    if level == 2 or (level == 3 and injury_return):
        if period == "preparatory":
            min_prep = L2_PERIOD_MIN_WEEKS.get("preparatory", 6)
            if pw_num >= min_prep:
                # После пика + неделя разгрузки → цикл заканчивается
                if evaluation.in_recovery_period or user.weeks_since_recovery == 0:
                    # Разгрузочная была — цикл завершён
                    return evaluation.in_recovery_period
        return False

    # L1 / L3 regular: recovery_period
    if period == "recovery_period":
        min_rec = L3_REGULAR_PERIOD_MIN_WEEKS.get("recovery_period", 2)
        if level == 1:
            from engine.constants import RECOVERY_PERIOD_MIN_WEEKS_L1
            min_rec = RECOVERY_PERIOD_MIN_WEEKS_L1
        if pw_num >= min_rec:
            return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
# start_new_cycle
# ══════════════════════════════════════════════════════════════════════════════

def start_new_cycle(
    user: "User",
    mode: Literal["advance", "stay", "redo"],
) -> dict:
    """
    Возвращает параметры нового цикла (не сохраняет в БД — это делает сервис).

    advance: level += 1, стартовый объём нового уровня
    stay:    тот же level, peak × 1.4
    redo:    тот же level, peak × 0.6 (провалил цикл)
    """
    level = user.level or 1
    injury_return = getattr(user, "injury_return_active", False)
    mac_peak = getattr(user, "macrocycle_peak_volume", None) or (
        user.weekly_target_minutes or get_level_start_volume(level, "base", injury_return)
    )
    ceiling = get_level_ceiling(level, injury_return)

    if mode == "advance":
        new_level = min(level + 1, 3)
        entry = "base"
        from engine.level_assignment import assign_initial_period
        new_period = assign_initial_period(new_level, entry)
        new_volume = get_level_start_volume(new_level, entry, False)
        return {
            "level": new_level,
            "entry_point": entry,
            "current_period": new_period,
            "weekly_target_minutes": new_volume,
            "cycle_number": (user.cycle_number or 1) + 1,
            "program_week_number": 1,
            "period_week_number": 1,
            "growth_streak": 0,
            "weeks_since_recovery": 0,
            "macrocycle_peak_volume": None,
        }

    if mode == "stay":
        new_vol = round_int(mac_peak * CYCLE_END_STAY_VOLUME_MULTIPLIER)
        new_vol = min(new_vol, ceiling)
        from engine.level_assignment import assign_initial_period
        new_period = assign_initial_period(level, user.entry_point or "base")
        return {
            "level": level,
            "current_period": new_period,
            "weekly_target_minutes": new_vol,
            "cycle_number": (user.cycle_number or 1) + 1,
            "program_week_number": 1,
            "period_week_number": 1,
            "growth_streak": 0,
            "weeks_since_recovery": 0,
            "macrocycle_peak_volume": None,
        }

    # redo
    new_vol = round_int(mac_peak * CYCLE_END_REDO_VOLUME_MULTIPLIER)
    new_vol = min(new_vol, ceiling)
    from engine.level_assignment import assign_initial_period
    new_period = assign_initial_period(level, user.entry_point or "base")
    return {
        "level": level,
        "current_period": new_period,
        "weekly_target_minutes": new_vol,
        "cycle_number": (user.cycle_number or 1) + 1,
        "program_week_number": 1,
        "period_week_number": 1,
        "growth_streak": 0,
        "weeks_since_recovery": 0,
        "macrocycle_peak_volume": None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# check_l1_long_stage_transition
# ══════════════════════════════════════════════════════════════════════════════

def check_l1_long_stage_transition(
    user: "User",
    recent_evals: list["WeekEvaluation"],
    easy_minutes_last_week: int,
) -> bool:
    """
    L1: переход long из стадии 1 в стадию 2.
    Условия:
    - ≥ 2 недели без боли (pain==3 ни разу)
    - Easy-тренировка достигла 40 мин
    """
    if getattr(user, "l1_long_independent", False):
        return False  # уже в стадии 2

    if len(recent_evals) < L1_LONG_STAGE2_NO_PAIN_WEEKS:
        return False

    last_n = recent_evals[-L1_LONG_STAGE2_NO_PAIN_WEEKS:]
    no_pain = not any(e.had_high_pain for e in last_n)
    easy_ok = easy_minutes_last_week >= L1_LONG_STAGE2_EASY_THRESHOLD

    return no_pain and easy_ok


# ══════════════════════════════════════════════════════════════════════════════
# check_injury_return_exit
# ══════════════════════════════════════════════════════════════════════════════

def check_injury_return_exit(
    user: "User",
    recent_evals: list["WeekEvaluation"],
) -> bool:
    """
    Выход из return-mode (L2 или L3 after break).

    Условия:
    - 4-6 успешных недель подряд
    - Текущий объём вышел на старт регулярного уровня
    - Нет боли за последние 2 недели
    """
    if not getattr(user, "injury_return_active", False):
        return False

    level = user.level or 1
    if level == 2:
        min_success = L2_RETURN_EXIT_SUCCESS_WEEKS_MIN
        target_vol = L2_RETURN_EXIT_VOLUME_TARGET
    else:
        min_success = L3_RETURN_EXIT_SUCCESS_WEEKS_MIN
        target_vol = L3_RETURN_EXIT_VOLUME_TARGET

    if len(recent_evals) < min_success:
        return False

    last_n = recent_evals[-min_success:]
    all_success = all(e.growth_eligible for e in last_n)
    no_pain = not any(e.had_high_pain for e in recent_evals[-2:])
    vol_ok = (user.weekly_target_minutes or 0) >= target_vol

    return all_success and no_pain and vol_ok


# ══════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ══════════════════════════════════════════════════════════════════════════════

def _can_run_20_min(user: "User") -> bool:
    """
    Может ли пользователь пробежать 20 мин без остановки.
    Берём из ответа онбординга q_continuous_run_test.
    """
    crt = getattr(user, "q_continuous_run_test", None)
    if crt == "yes":
        return True
    if crt == "no":
        return False
    # unsure / None: смотрим на l1_long_independent как косвенный признак
    return getattr(user, "l1_long_independent", False)


def _avg_completion(evals: list["WeekEvaluation"]) -> float:
    if not evals:
        return 0.0
    return sum(e.completion_rate for e in evals) / len(evals)


def _get_cycle_max_weeks(level: int, injury_return: bool) -> int:
    if level == 1:
        return L1_CYCLE_MAX_WEEKS
    if level == 2:
        return L2_CYCLE_MAX_WEEKS
    if level == 3:
        return L3_RETURN_CYCLE_MAX_WEEKS if injury_return else L3_REGULAR_CYCLE_MAX_WEEKS
    return L3_REGULAR_CYCLE_MAX_WEEKS
