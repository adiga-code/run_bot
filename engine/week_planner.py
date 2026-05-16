"""
engine/week_planner.py
Генератор недельного плана (WeekPlan + DayPlan).
Spec разделы 3.5, 3.6, 3.10.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

from engine.constants import (
    L1_LONG_RATIO_DEPENDENT, L1_LONG_MAX_RATIO, L1_LONG_STAGE2_EASY_THRESHOLD,
    L2_RECOVERY_RUN_MINUTES, L2_AEROBIC_RUN_RANGE,
    L3_REGULAR_RECOVERY_RUN_MINUTES, L3_REGULAR_AEROBIC_RUN_RANGE,
    L1_STRENGTH_MINUTES, L2_STRENGTH_MINUTES, L3_REGULAR_STRENGTH_MINUTES,
    L3_RETURN_STRENGTH_MINUTES,
    MAX_INTENSITY_PER_WEEK, MAX_INTERVALS_PER_WEEK,
    INTENSITY_NO_PAIN_RECENT_WEEKS, INTENSITY_LIGHT_LIMIT_4WEEKS,
    INTENSITY_RECOVERY_LIMIT_4WEEKS, L1_INTENSITY_MIN_WEEK_OF_PROGRAM,
    L2_INTERVALS_AFTER_SUCCESS_WEEKS,
    AEROBIC_LONG_MIN_GAP,
    INJURY_RETURN_INTRO_LONG_RATIO,
    is_injury_return_intro,
    get_long_max_ratio, round_int,
)

if TYPE_CHECKING:
    from database.models import User


# ══════════════════════════════════════════════════════════════════════════════
# Вспомогательные датаклассы (не ORM-модели — для генерации)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DaySlot:
    """Один день в сгенерированном плане."""
    day_of_week: int          # 1=Пн..7=Вс
    day_type: str             # run/strength/recovery/rest/mobility
    run_subtype: str | None   # easy/aerobic/recovery_run/long/tempo/intervals/run_walk
    planned_minutes: int
    intensity: str | None     # null/z3_inclusions/tempo/intervals
    is_key: bool = False


@dataclass
class WeekBlueprint:
    """Промежуточное представление недели перед записью в БД."""
    weekly_target_minutes: int
    is_recovery_week: bool
    days: list[DaySlot] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ══════════════════════════════════════════════════════════════════════════════

def _parse_weekdays(available_weekdays: str) -> list[int]:
    """'1,3,5' → [1, 3, 5]. Сортирует по возрастанию."""
    if not available_weekdays:
        return [1, 3, 5]
    return sorted(int(d) for d in available_weekdays.split(",") if d.strip())


_IDEAL_RUN_DAYS = {
    "l1": 3,  # L1: до 3 беговых
    "l2": 3,  # L2 и L3-return: минимум 3 беговых
    "l3": 5,  # L3 regular: до 5 беговых
}
_MAX_STRENGTH_DAYS = 2  # силовых не более 2 в любом случае


def _run_strength_split(level: int, injury_return: bool, n: int) -> tuple[int, int]:
    """
    Возвращает (n_run_total, n_strength) по приоритету «бег первый».
    Сначала занимаем беговые слоты по методике уровня,
    силовые добавляем в оставшиеся дни (макс. 2).
    """
    if level == 3 and not injury_return:
        ideal_run = _IDEAL_RUN_DAYS["l3"]
    elif level == 1:
        ideal_run = _IDEAL_RUN_DAYS["l1"]
    else:
        ideal_run = _IDEAL_RUN_DAYS["l2"]
    n_run_total = max(1, min(ideal_run, n))
    n_strength = min(_MAX_STRENGTH_DAYS, max(0, n - n_run_total))
    return n_run_total, n_strength


def _get_strength_minutes(level: int, period: str, injury_return: bool) -> int:
    """Длительность силовой тренировки в минутах."""
    if level == 1:
        return L1_STRENGTH_MINUTES.get(period, 30)
    if level == 2:
        return L2_STRENGTH_MINUTES.get(period, 30)
    if level == 3:
        tbl = L3_RETURN_STRENGTH_MINUTES if injury_return else L3_REGULAR_STRENGTH_MINUTES
        val = tbl.get(period, 40)
        return val[0] if isinstance(val, tuple) else val
    return 30


def _get_level_key(level: int, injury_return: bool) -> str:
    if level == 1:
        return "L1"
    if level == 2:
        return "L2"
    if level == 3:
        return "L3_RETURN" if injury_return else "L3_REGULAR"
    return "L3_REGULAR"


# ══════════════════════════════════════════════════════════════════════════════
# Расчёт минут на тренировки
# ══════════════════════════════════════════════════════════════════════════════

def split_running_minutes(
    weekly_target: int,
    level: int,
    period: str,
    injury_return: bool,
    n_run_days: int,
    is_long_independent: bool,
    is_recovery_week: bool,
    program_week_number: int = 0,
) -> dict[str, int]:
    """
    Разбивает недельный объём бега по типам.
    Возвращает: {long, easy, aerobic, recovery_run}.
    """
    if n_run_days == 0:
        return {"long": 0, "easy": 0, "aerobic": 0, "recovery_run": 0}

    long_ratio = get_long_max_ratio(level, period, injury_return)

    # ── Long ────────────────────────────────────────────────────────────────────────────────────
    if level == 1 and not is_long_independent:
        # Стадия 1: long = min(avg × 1.3, target × 0.35)
        avg_run = weekly_target / n_run_days
        long = round_int(min(avg_run * L1_LONG_RATIO_DEPENDENT, weekly_target * L1_LONG_MAX_RATIO))
    else:
        # L2 / L3 / L1 стадия 2: независимый long ≤ ratio × target
        long = round_int(weekly_target * long_ratio)

    long = min(long, weekly_target)

    remaining = weekly_target - long
    n_other = n_run_days - 1  # дни без long

    if n_other <= 0:
        return {"long": long, "easy": 0, "aerobic": 0, "recovery_run": 0}

    per_other = round_int(remaining / n_other)

    # ── Вводный период injury_return: только лёгкий бег, укороченный long ────────────────────────
    if is_injury_return_intro(injury_return, program_week_number):
        long = round_int(weekly_target * INJURY_RETURN_INTRO_LONG_RATIO)
        long = min(long, weekly_target)
        per_other = round_int((weekly_target - long) / n_other)
        return {"long": long, "easy": per_other, "aerobic": 0, "recovery_run": 0}

    # ── Тип остальных беговых ──────────────────────────────────────────────────────────────────────
    if level == 1:
        # L1: all easy / run-walk
        return {"long": long, "easy": per_other, "aerobic": 0, "recovery_run": 0}

    if level == 2 or (level == 3 and injury_return):
        # L2 / L3 return: recovery_run + aerobic
        # Один recovery_run (40 мин), остальные — aerobic
        if n_other >= 2:
            rec_min = L2_RECOVERY_RUN_MINUTES
            aerobic_min = round_int((remaining - rec_min) / (n_other - 1))
            # At low L2 volume aerobic < recovery_run is not valid; skip recovery_run instead.
            if aerobic_min < rec_min:
                aerobic_min = round_int(remaining / n_other)
                return {"long": long, "easy": aerobic_min, "aerobic": 0, "recovery_run": 0}
            # Enforce hierarchy: aerobic must be shorter than long.
            if aerobic_min >= long:
                excess = aerobic_min - long + AEROBIC_LONG_MIN_GAP
                long += excess
                aerobic_min -= excess
            return {"long": long, "easy": 0, "aerobic": aerobic_min, "recovery_run": rec_min}
        return {"long": long, "easy": 0, "aerobic": per_other, "recovery_run": 0}

    # L3 regular
    rec_min = L3_REGULAR_RECOVERY_RUN_MINUTES
    if n_other >= 2:
        aerobic_min = round_int((remaining - rec_min) / (n_other - 1))
        # Enforce hierarchy: aerobic must be shorter than long.
        if aerobic_min >= long:
            excess = aerobic_min - long + AEROBIC_LONG_MIN_GAP
            long += excess
            aerobic_min -= excess
        return {"long": long, "easy": 0, "aerobic": aerobic_min, "recovery_run": rec_min}
    return {"long": long, "easy": 0, "aerobic": 0, "recovery_run": per_other}


# ══════════════════════════════════════════════════════════════════════════════
# Проверка: можно ли добавить интенсивность
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class WeekStats:
    """Краткая статистика прошедшей недели."""
    growth_eligible: bool
    light_days: int
    recovery_days: int
    had_high_pain: bool   # был ли pain==3 хоть раз


def can_add_intensity(
    level: int,
    period: str,
    injury_return: bool,
    program_week_number: int,
    growth_streak: int,
    recent_weeks: list[WeekStats],  # последние недели, от старых к новым
) -> bool:
    """
    Проверяет условия добавления tempo/intervals (spec 3.10.1).
    """
    level_key = _get_level_key(level, injury_return)
    max_per_week = MAX_INTENSITY_PER_WEEK.get((level_key, period), 0)
    if max_per_week == 0:
        return False

    # injury_return intro: интенсивность запрещена в первые недели возврата
    if is_injury_return_intro(injury_return, program_week_number):
        return False

    # L1 base: не раньше 8-й недели
    if level == 1 and period == "base" and program_week_number < L1_INTENSITY_MIN_WEEK_OF_PROGRAM:
        return False

    # Нет достаточно истории
    if not recent_weeks:
        return False

    # L2 base: нужно 3 успешных недели подряд
    if level == 2 and period == "base":
        if growth_streak < L2_INTERVALS_AFTER_SUCCESS_WEEKS:
            return False

    # Нет боли за последние 2 недели
    pain_weeks = recent_weeks[-INTENSITY_NO_PAIN_RECENT_WEEKS:]
    if any(w.had_high_pain for w in pain_weeks):
        return False

    # Light ≤ 2 / нед, Recovery ≤ 1 / нед (среднее за 4 нед)
    check_weeks = recent_weeks[-4:] if len(recent_weeks) >= 4 else recent_weeks
    if check_weeks:
        avg_light = sum(w.light_days for w in check_weeks) / len(check_weeks)
        avg_rec = sum(w.recovery_days for w in check_weeks) / len(check_weeks)
        if avg_light > INTENSITY_LIGHT_LIMIT_4WEEKS:
            return False
        if avg_rec > INTENSITY_RECOVERY_LIMIT_4WEEKS:
            return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
# Раскладка дней
# ══════════════════════════════════════════════════════════════════════════════

def _layout_days(
    available: list[int],
    level: int,
    period: str,
    injury_return: bool,
    minutes: dict[str, int],
    add_intensity: bool,
    is_recovery_week: bool,
) -> list[DaySlot]:
    """
    Распределяет тренировки по доступным дням недели.

    Правила позиционирования (spec 3.5.3):
    - Long — последний доступный день
    - Силовая не ставится за день до long и не перед intensity
    - Между беговыми ≥ 1 день без бега (если возможно)
    - L3 regular: силовая + лёгкий/восстановительный бег — совмещение в один день
    """
    n = len(available)
    slots: dict[int, DaySlot] = {}

    strength_min = _get_strength_minutes(level, period, injury_return)
    level_key = _get_level_key(level, injury_return)

    # ── Беговые дни первичны, силовые заполняют остаток ────────────────────────────────────────────────
    n_run_total, n_strength = _run_strength_split(level, injury_return, n)

    # ── Long → последний день ────────────────────────────────────────────────────────────────────────
    long_day = available[-1]
    slots[long_day] = DaySlot(
        day_of_week=long_day,
        day_type="run",
        run_subtype="long",
        planned_minutes=minutes["long"],
        intensity=None,
        is_key=True,
    )

    # ── Остальные дни (не long) ────────────────────────────────────────────────────────────────────────
    other_days = [d for d in available if d != long_day]

    # Собираем типы тренировок для оставшихся дней
    run_subtypes: list[str] = []
    if level == 1:
        run_subtypes = ["easy"] * (n_run_total - 1)
    elif level == 2 or (level == 3 and injury_return):
        # 1 recovery_run + N-1 aerobic; при низком объёме (easy > 0) — easy
        other_run = n_run_total - 1
        if other_run > 0 and minutes.get("recovery_run", 0) > 0:
            run_subtypes = ["recovery_run"] + ["aerobic"] * max(0, other_run - 1)
        elif minutes.get("easy", 0) > 0:
            run_subtypes = ["easy"] * other_run
        else:
            run_subtypes = ["aerobic"] * other_run
    else:
        # L3 regular
        other_run = n_run_total - 1
        if other_run > 0 and minutes.get("recovery_run", 0) > 0:
            run_subtypes = ["recovery_run"] + ["aerobic"] * max(0, other_run - 1)
        else:
            run_subtypes = ["aerobic"] * other_run

    # Заменяем одну беговую на intensity (если добавляем)
    if add_intensity and run_subtypes and not is_recovery_week:
        max_intensity = MAX_INTENSITY_PER_WEEK.get((level_key, period), 0)
        if max_intensity >= 1:
            # Заменяем первую aerobic (или easy) на intervals
            for i, sub in enumerate(run_subtypes):
                if sub in ("aerobic", "easy"):
                    run_subtypes[i] = "intervals"
                    break

    # ── Раскладка: силовые и беговые по оставшимся дням ───────────────────
    # Избегаем ставить силовую за день до long
    pre_long_day = long_day - 1  # может не быть в available
    forbidden_strength = {pre_long_day} if pre_long_day in other_days else set()

    strength_days: list[int] = []
    run_days: list[int] = []

    # Стараемся разнести тренировки одного типа: ≥ 1 день без бега между беговыми (если возможно)
    # L3 regular: разрешаем совмещение силовой + лёгкого бега
    l3_combo = (level == 3 and not injury_return)

    last_run_day: int | None = None
    for i, day in enumerate(other_days):
        days_remaining = len(other_days) - i
        strength_still_needed = n_strength - len(strength_days)
        run_still_needed = (n_run_total - 1) - len(run_days)

        would_be_consecutive_strength = bool(strength_days) and day == strength_days[-1] + 1
        would_be_consecutive_run = last_run_day is not None and day == last_run_day + 1

        can_be_strength = (
            strength_still_needed > 0
            and day not in forbidden_strength
            and not would_be_consecutive_strength
        )
        can_be_run_ideal = run_still_needed > 0 and not would_be_consecutive_run
        # Вынужденная беговая: оставшихся дней ровно столько, сколько нужно беговых
        must_be_run = run_still_needed > 0 and days_remaining <= run_still_needed

        if must_be_run and strength_still_needed == 0:
            run_days.append(day)
            last_run_day = day
        elif can_be_strength and can_be_run_ideal:
            # Оба варианта без смежности — берём тот тип, которого нужно больше
            if strength_still_needed >= run_still_needed:
                strength_days.append(day)
            else:
                run_days.append(day)
                last_run_day = day
        elif can_be_strength:
            strength_days.append(day)
        elif can_be_run_ideal:
            run_days.append(day)
            last_run_day = day
        elif strength_still_needed > 0 and day not in forbidden_strength:
            strength_days.append(day)  # вынужденная смежная силовая
        else:
            run_days.append(day)  # вынужденная смежная беговая
            last_run_day = day

    # Если силовых дней не хватает — добираем из run_days (без ограничения на смежность)
    while len(strength_days) < n_strength and run_days:
        strength_days.append(run_days.pop(0))

    # ── Заполняем слоты для силовых ──────────────────────────────────────────────────────
    key_strength_assigned = False
    for i, day in enumerate(strength_days):
        is_key = not key_strength_assigned
        key_strength_assigned = True

        if l3_combo and day in run_days:
            pass

        slots[day] = DaySlot(
            day_of_week=day,
            day_type="strength",
            run_subtype=None,
            planned_minutes=strength_min,
            intensity=None,
            is_key=is_key,
        )

    # ── Заполняем слоты для беговых ────────────────────────────────────────────────────────
    # Первая беговая (кроме long) — ключевая
    key_run_assigned = False
    for i, day in enumerate(run_days):
        if i < len(run_subtypes):
            sub = run_subtypes[i]
        else:
            sub = "easy" if level == 1 else "aerobic"

        if sub == "easy":
            mins = minutes.get("easy", 30)
        elif sub == "recovery_run":
            mins = minutes.get("recovery_run", 40)
        elif sub in ("aerobic",):
            mins = minutes.get("aerobic", 50)
        elif sub == "intervals":
            mins = minutes.get("aerobic", 50)
        elif sub == "run_walk":
            mins = minutes.get("easy", 30)
        else:
            mins = minutes.get("aerobic", 50)

        intensity_val = None
        if sub == "intervals":
            intensity_val = "intervals"
        elif sub == "tempo":
            intensity_val = "tempo"

        is_key = not key_run_assigned and sub not in ("recovery_run",)
        if is_key:
            key_run_assigned = True

        slots[day] = DaySlot(
            day_of_week=day,
            day_type="run",
            run_subtype=sub,
            planned_minutes=mins,
            intensity=intensity_val,
            is_key=is_key,
        )

    # ── Дни без тренировки → rest ────────────────────────────────────────────────────────
    all_days_in_week = set(range(1, 8))
    assigned_days = set(slots.keys())
    for day in all_days_in_week - assigned_days:
        slots[day] = DaySlot(
            day_of_week=day,
            day_type="rest",
            run_subtype=None,
            planned_minutes=0,
            intensity=None,
            is_key=False,
        )

    return sorted(slots.values(), key=lambda s: s.day_of_week)


# ══════════════════════════════════════════════════════════════════════════════
# Главная функция
# ══════════════════════════════════════════════════════════════════════════════

def build_week_plan(
    user: "User",
    week_number: int,
    period: str,
    target_minutes: int,
    is_recovery_week: bool,
    available_weekdays: list[int],
    add_intensity: bool = False,
) -> WeekBlueprint:
    """
    Строит недельный план (WeekBlueprint) по параметрам пользователя.

    Результат затем сохраняется в WeekPlan + DayPlan через WeekPlanService.
    """
    level = user.level or 1
    injury_return = getattr(user, "injury_return_active", False)
    is_long_independent = getattr(user, "l1_long_independent", False)

    if not available_weekdays:
        available_weekdays = _parse_weekdays(user.available_weekdays or "1,3,5")

    n_run_days = _count_run_days(level, period, injury_return, len(available_weekdays))

    minutes = split_running_minutes(
        weekly_target=target_minutes,
        level=level,
        period=period,
        injury_return=injury_return,
        n_run_days=n_run_days,
        is_long_independent=is_long_independent,
        is_recovery_week=is_recovery_week,
        program_week_number=week_number,
    )

    days = _layout_days(
        available=available_weekdays,
        level=level,
        period=period,
        injury_return=injury_return,
        minutes=minutes,
        add_intensity=add_intensity and not is_recovery_week,
        is_recovery_week=is_recovery_week,
    )

    return WeekBlueprint(
        weekly_target_minutes=target_minutes,
        is_recovery_week=is_recovery_week,
        days=days,
    )


def _count_run_days(level: int, period: str, injury_return: bool, n_total: int) -> int:
    """
    Количество беговых дней (включая long) для данного уровня.

    Логика n_strength здесь точно повторяет _layout_days, чтобы
    split_running_minutes делил объём на реальное число беговых дней.
    """
    n_run_total, _ = _run_strength_split(level, injury_return, n_total)
    return n_run_total


def parse_available_weekdays(s: str | None) -> list[int]:
    """Публичный парсер строки дней '1,3,5' → [1,3,5]."""
    return _parse_weekdays(s or "1,3,5")
