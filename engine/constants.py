"""
engine/constants.py
Все числовые параметры методики собраны в одном месте.
Тренер может менять цифры здесь без знания кода.
"""
from __future__ import annotations


# ═════════════════════════════════════════════════════════════════════════════
# ОБЩИЕ ПАРАМЕТРЫ ПРОГРЕССИИ
# ═════════════════════════════════════════════════════════════════════════════

GROWTH_MULTIPLIER: float = 1.10        # +10% при успешной неделе (по умолчанию)
RECOVERY_MULTIPLIER: float = 0.60      # разгрузочная неделя = −40% от пика
SUCCESS_THRESHOLD: float = 0.85        # 85% — единый порог во всей системе

GROWTH_STREAK_FOR_RECOVERY: int = 3    # 3 успешных недели подряд → разгрузка
FAILSAFE_WEEKS_WITHOUT_RECOVERY: int = 6  # принудительная разгрузка

# Light/Recovery как блокеры успешной недели
MAX_LIGHT_DAYS_PER_WEEK: int = 2       # ≥ 3 → неделя неуспешная
MAX_RECOVERY_DAYS_PER_WEEK: int = 1    # ≥ 2 → неделя неуспешная

# Откат (red flag)
ROLLBACK_PAIN_DAYS: int = 3            # 3 дня pain==3 подряд → red flag
GROWTH_BLOCK_MILD_PAIN_DAYS: int = 3   # 3 дня pain==2 подряд → блок роста (не откат)
ROLLBACK_AUTO_LIFT_WEEKS: int = 1      # 1 успешная нед при активном флаге → снять

# Версия Light
LIGHT_VOLUME_MULTIPLIER: float = 0.80  # −20% к плановому объёму

# Возврат после боли (раздел 3.7.4)
PAIN_RETURN_LIGHT_DAYS: int = 1        # 1 день Light после боли


# ═════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 1 — новичок
# ═════════════════════════════════════════════════════════════════════════════

L1_START_VOLUME_BASE_IN: int = 60      # мин/нед — точка входа base_in
L1_START_VOLUME_BASE: int = 120        # мин/нед — точка входа base
L1_CEILING: int = 240                  # мин/нед — жёсткий потолок

L1_MIN_DAYS: int = 3
L1_MAX_RUNNING: int = 3
L1_MIN_STRENGTH: int = 1               # ключевая, обязательна
L1_MAX_STRENGTH: int = 2

L1_CYCLE_MIN_WEEKS: int = 16
L1_CYCLE_MAX_WEEKS: int = 24

L1_PERIOD_MIN_WEEKS: dict[str, int] = {
    "base_in": 4,
    "base": 6,
    "specialized": 4,
    "recovery_period": 2,
}

L1_INTENSITY_MIN_WEEK_OF_PROGRAM: int = 8  # tempo/intervals не ранее 8-й недели

L1_STRENGTH_MINUTES: dict[str, int] = {
    "base_in": 30,
    "base": 30,
    "specialized": 30,
}

L1_LONG_RATIO_DEPENDENT: float = 1.30   # стадия 1: long = avg × 1.3
L1_LONG_MAX_RATIO: float = 0.35         # long ≤ 35% недельного объёма

# Переход long стадия 1 → 2
L1_LONG_STAGE2_NO_PAIN_WEEKS: int = 2   # 2 нед без боли подряд
L1_LONG_STAGE2_EASY_THRESHOLD: int = 40 # easy ≥ 40 мин

L1_ZONE_DISTRIBUTION: dict[str, float] = {
    "z1_z2": 0.80, "z3": 0.15, "z4": 0.05, "z5": 0.00,
}


# ═════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 2 — средний
# ═════════════════════════════════════════════════════════════════════════════

L2_START_VOLUME: int = 150             # нижняя граница 150-240
L2_CEILING: int = 300                  # нижняя граница 300-420

L2_MIN_DAYS: int = 3
L2_MAX_RUNNING: int = 4
L2_MIN_STRENGTH: int = 1
L2_MAX_STRENGTH: int = 2

L2_CYCLE_MIN_WEEKS: int = 8
L2_CYCLE_MAX_WEEKS: int = 16

L2_PERIOD_MIN_WEEKS: dict[str, int] = {
    "base": 6,
    "preparatory": 6,
    # разгрузочная — 1 неделя в конце цикла
}

L2_INTERVALS_AFTER_SUCCESS_WEEKS: int = 3  # после 3 успешных нед подряд

L2_STRENGTH_MINUTES: dict[str, int] = {
    "base": 30,
    "preparatory": 40,
}

L2_LONG_MAX_RATIO: float = 0.35        # ≤ 35% недели и ≤ потолка × 0.35

AEROBIC_LONG_MIN_GAP: int = 5          # минут: aerobic должен быть короче long минимум на столько

L2_ZONE_DISTRIBUTION: dict[str, float] = {
    "z1_z2": 0.75, "z3": 0.20, "z4": 0.05,
}

L2_RECOVERY_RUN_MINUTES: int = 40
L2_AEROBIC_RUN_RANGE: tuple[int, int] = (50, 70)
L2_LONG_RANGE: tuple[int, int] = (70, 100)

L2_TEMPO_STRUCTURE: dict = {
    "warmup": 15,
    "main_min": 15, "main_max": 40,
    "cooldown": 15,
    "main_zone": "z3",
}
L2_INTERVALS_STRUCTURE: dict = {
    "warmup": 15,
    "reps_min": 5, "reps_max": 7,
    "rep_duration_min": 3, "rep_duration_max": 5,
    "rep_zone": "z3_z4",
    "rest_min": 2, "rest_max": 4, "rest_zone": "z1",
    "cooldown": 15,
}


# ═════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 3 REGULAR — продвинутый
# ═════════════════════════════════════════════════════════════════════════════

L3_REGULAR_START_VOLUME: int = 240     # нижняя граница 240-360
L3_REGULAR_CEILING: int = 600          # верхняя граница 360-600

L3_REGULAR_MIN_DAYS: int = 5
L3_REGULAR_MAX_RUNNING: int = 5        # 4-5 беговых
L3_REGULAR_MIN_STRENGTH: int = 2       # 2 силовых в плане (обязательно)
L3_REGULAR_KEY_STRENGTH: int = 1       # из них 1 ключевая (для условия роста)
L3_REGULAR_MAX_STRENGTH: int = 2

L3_REGULAR_CYCLE_MIN_WEEKS: int = 14   # base 6 + prep 6 + recovery 2
L3_REGULAR_CYCLE_MAX_WEEKS: int = 22

L3_REGULAR_PERIOD_MIN_WEEKS: dict[str, int] = {
    "base": 6,
    "preparatory": 6,
    "recovery_period": 2,              # 2-3 недели (не одна!)
}

L3_REGULAR_GROWTH_MULTIPLIERS: dict[str, float | None] = {
    "base": 1.10,
    "preparatory": 1.15,               # +15% форсированный рост
    "recovery_period": None,           # без роста
}

L3_REGULAR_STRENGTH_MINUTES: dict[str, tuple[int, int]] = {
    "base": (30, 50),
    "preparatory": (35, 50),
}

# Long: в base ≤ 35%, в preparatory ≤ 40%
L3_REGULAR_LONG_RATIO_BASE: float = 0.35
L3_REGULAR_LONG_RATIO_PREP: float = 0.40

L3_REGULAR_ZONE_DISTRIBUTION: dict[str, float] = {
    "z1_z2": 0.70, "z3": 0.15, "z4": 0.10, "z5": 0.05,
}

L3_REGULAR_RECOVERY_RUN_MINUTES: int = 60
L3_REGULAR_AEROBIC_RUN_RANGE: tuple[int, int] = (70, 90)
L3_REGULAR_LONG_RANGE_BASE: tuple[int, int] = (90, 120)
L3_REGULAR_LONG_RANGE_PREP: tuple[int, int] = (110, 120)
L3_REGULAR_MOBILITY_RANGE: tuple[int, int] = (20, 25)

L3_REGULAR_TEMPO_STRUCTURE: dict = {
    "warmup": 20,
    "main_min": 25, "main_max": 35,
    "cooldown": 15,
    "main_zone": "z3",
}
L3_REGULAR_INTERVALS_BASE: dict = {
    "warmup": 15,
    "reps_min": 6, "reps_max": 8,
    "rep_duration_min": 2, "rep_duration_max": 4,
    "rep_zone": "z4",
    "rest_min": 2, "rest_max": 3, "rest_zone": "z1",
    "cooldown": 15,
}
L3_REGULAR_INTERVALS_PREP: dict = {
    "warmup": 20,
    "reps_min": 6, "reps_max": 6,
    "rep_duration_min": 4, "rep_duration_max": 4,
    "rep_zone": "z3.5_z4",
    "rest_min": 3, "rest_max": 3, "rest_zone": "z1",
    "cooldown": 10,
}

L3_REGULAR_RUN_WALK_ALLOWED: bool = False
L3_REGULAR_STRENGTH_RUN_COMBO_ALLOWED: bool = True  # силовая + лёгкий бег в один день
L3_REGULAR_RECOVERY_PERIOD_MULTIPLIER: float = 0.60


# ═════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 3 AFTER BREAK — return-mode
# ═════════════════════════════════════════════════════════════════════════════

L3_RETURN_START_VOLUME: int = 180      # ниже чем regular (240)
L3_RETURN_CEILING: int = 420

L3_RETURN_MIN_DAYS: int = 4
L3_RETURN_CYCLE_MIN_WEEKS: int = 8
L3_RETURN_CYCLE_MAX_WEEKS: int = 12

L3_RETURN_EXIT_SUCCESS_WEEKS_MIN: int = 4   # 4-6 успешных нед для выхода
L3_RETURN_EXIT_SUCCESS_WEEKS_MAX: int = 6
L3_RETURN_EXIT_VOLUME_TARGET: int = 240     # старт regular L3 — объём выхода

L3_RETURN_GROWTH_MULTIPLIER: float = 1.10  # стандарт, без +15%
L3_RETURN_RUN_WALK_ALLOWED: bool = True    # в первые недели

L3_RETURN_STRENGTH_MINUTES: dict[str, int] = {
    "base": 40,
    "preparatory": 50,
}

L3_RETURN_ZONE_DISTRIBUTION: dict[str, float] = {
    "z1_z2": 0.70, "z3": 0.20, "z4": 0.10, "z5": 0.00,
}


# ═════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 2 AFTER BREAK — return-mode
# ═════════════════════════════════════════════════════════════════════════════

L2_RETURN_CYCLE_MIN_WEEKS: int = 4
L2_RETURN_CYCLE_MAX_WEEKS: int = 6
L2_RETURN_EXIT_SUCCESS_WEEKS_MIN: int = 4
L2_RETURN_EXIT_VOLUME_TARGET: int = 150   # старт regular L2
L2_RETURN_RUN_WALK_ALLOWED: bool = True


# ═════════════════════════════════════════════════════════════════════════════
# RECOVERY PERIOD (multi-week) — только L1 и L3 regular
# ═════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════
# INJURY RETURN — вводный период (первые недели после перерыва)
# ═════════════════════════════════════════════════════════════════════════════

INJURY_RETURN_INTRO_WEEKS: int = 2          # первые N недель injury_return: только лёгкий бег
INJURY_RETURN_INTRO_LONG_RATIO: float = 0.30  # укороченный long (вместо обычных 0.35)


def is_injury_return_intro(injury_return: bool, program_week_number: int) -> bool:
    """True, если это первые INJURY_RETURN_INTRO_WEEKS недели возврата после перерыва."""
    return injury_return and 1 <= program_week_number <= INJURY_RETURN_INTRO_WEEKS


RECOVERY_PERIOD_MULTIPLIER: float = 0.60
RECOVERY_PERIOD_MIN_WEEKS_L1: int = 2
RECOVERY_PERIOD_MAX_WEEKS_L1: int = 4
RECOVERY_PERIOD_MIN_WEEKS_L3: int = 2
RECOVERY_PERIOD_MAX_WEEKS_L3: int = 3
RECOVERY_PERIOD_NO_GROWTH: bool = True

# Триггеры расширения recovery_period (дефолт 2 → до 3/4)
RECOVERY_EXTEND_TRIGGER_RED_FLAG: bool = True
RECOVERY_EXTEND_LIGHT_RECOVERY_AVG: float = 1.5   # avg (light+recovery)/нед ≥ 1.5
RECOVERY_EXTEND_PEAK_RATIO: float = 0.90           # peak ≥ 90% потолка → +1 нед


def compute_recovery_period_weeks(
    level: int,
    injury_return: bool,
    cycle_stats: dict,
) -> int:
    """
    Длительность recovery_period в конце макроцикла.

    cycle_stats содержит:
        had_red_flag: bool
        light_days_total: int
        recovery_days_total: int
        total_weeks: int
        peak_volume: int
        ceiling: int
    """
    if level == 2:
        return 1  # L2: одна разгрузочная неделя
    if level == 3 and injury_return:
        return 1  # L3 after break: как L2

    # L1 или L3 regular: дефолт 2, +1 за каждый триггер
    weeks = 2
    triggers = 0

    if cycle_stats.get("had_red_flag"):
        triggers += 1

    total_weeks = cycle_stats.get("total_weeks", 1)
    avg_weak = (
        cycle_stats.get("light_days_total", 0)
        + cycle_stats.get("recovery_days_total", 0)
    ) / max(total_weeks, 1)
    if avg_weak >= RECOVERY_EXTEND_LIGHT_RECOVERY_AVG:
        triggers += 1

    ceiling = cycle_stats.get("ceiling", 1)
    if ceiling > 0 and cycle_stats.get("peak_volume", 0) >= RECOVERY_EXTEND_PEAK_RATIO * ceiling:
        triggers += 1

    weeks += triggers
    if level == 3:
        return min(weeks, RECOVERY_PERIOD_MAX_WEEKS_L3)
    if level == 1:
        return min(weeks, RECOVERY_PERIOD_MAX_WEEKS_L1)
    return weeks


# ═════════════════════════════════════════════════════════════════════════════
# КОНЕЦ ЦИКЛА
# ═════════════════════════════════════════════════════════════════════════════

CYCLE_END_STAY_VOLUME_MULTIPLIER: float = 1.40   # peak × 1.4 при остатке
CYCLE_END_REDO_VOLUME_MULTIPLIER: float = 0.60   # peak × 0.6 при провале
# (пользователь уже на уровне recovery_period — продолжаем плавно)


# ═════════════════════════════════════════════════════════════════════════════
# ИНТЕНСИВНОСТЬ (tempo / intervals)
# ═════════════════════════════════════════════════════════════════════════════

INTENSITY_REQUIRES_SUCCESSFUL_BLOCK: bool = True
INTENSITY_NO_PAIN_RECENT_WEEKS: int = 2         # 2 нед без боли
INTENSITY_LIGHT_LIMIT_4WEEKS: int = 2           # средн. Light ≤ 2/нед
INTENSITY_RECOVERY_LIMIT_4WEEKS: int = 1        # средн. Recovery ≤ 1/нед

MAX_INTENSITY_PER_WEEK: dict[tuple[str, str], int] = {
    ("L1", "base_in"):         0,
    ("L1", "base"):            1,   # tempo ИЛИ intervals
    ("L1", "specialized"):     2,
    ("L1", "recovery_period"): 0,
    ("L2", "base"):            1,
    ("L2", "preparatory"):     2,
    ("L3_REGULAR", "base"):        2,
    ("L3_REGULAR", "preparatory"): 2,
    ("L3_REGULAR", "recovery_period"): 0,
    ("L3_RETURN", "base"):         1,
    ("L3_RETURN", "preparatory"):  2,
}

MAX_INTERVALS_PER_WEEK: int = 1     # на любом уровне/периоде


def get_growth_multiplier(level: int, period: str, injury_return: bool) -> float:
    """
    Множитель роста для текущей недели.
    +10% по умолчанию, +15% только для L3 regular в preparatory.
    """
    if level == 3 and not injury_return and period == "preparatory":
        return L3_REGULAR_GROWTH_MULTIPLIERS["preparatory"]  # 1.15
    return GROWTH_MULTIPLIER  # 1.10


def get_level_ceiling(level: int, injury_return: bool = False) -> int:
    """Жёсткий потолок объёма (мин/нед) для данного уровня/режима."""
    if level == 1:
        return L1_CEILING
    if level == 2:
        return L2_CEILING
    if level == 3:
        return L3_RETURN_CEILING if injury_return else L3_REGULAR_CEILING
    return L3_REGULAR_CEILING


def get_level_start_volume(level: int, entry_point: str, injury_return: bool = False) -> int:
    """Стартовый объём (нижняя граница) для уровня и точки входа."""
    if level == 1:
        return L1_START_VOLUME_BASE_IN if entry_point == "base_in" else L1_START_VOLUME_BASE
    if level == 2:
        return L2_START_VOLUME
    if level == 3:
        return L3_RETURN_START_VOLUME if injury_return else L3_REGULAR_START_VOLUME
    return L3_REGULAR_START_VOLUME


def get_long_max_ratio(level: int, period: str, injury_return: bool = False) -> float:
    """Максимальная доля long от недельного объёма."""
    if level == 1:
        return L1_LONG_MAX_RATIO
    if level == 2:
        return L2_LONG_MAX_RATIO
    if level == 3:
        if not injury_return and period == "preparatory":
            return L3_REGULAR_LONG_RATIO_PREP
        return L3_REGULAR_LONG_RATIO_BASE
    return 0.35


def get_min_days(level: int, injury_return: bool = False) -> int:
    """Минимальное количество доступных дней для уровня."""
    if level == 1:
        return L1_MIN_DAYS
    if level == 2:
        return L2_MIN_DAYS
    if level == 3:
        return L3_RETURN_MIN_DAYS if injury_return else L3_REGULAR_MIN_DAYS
    return L3_REGULAR_MIN_DAYS


def get_cycle_max_weeks(level: int, injury_return: bool = False) -> int:
    """Максимальная длина цикла в неделях."""
    if level == 1:
        return L1_CYCLE_MAX_WEEKS
    if level == 2:
        return L2_CYCLE_MAX_WEEKS
    if level == 3:
        return L3_RETURN_CYCLE_MAX_WEEKS if injury_return else L3_REGULAR_CYCLE_MAX_WEEKS
    return L3_REGULAR_CYCLE_MAX_WEEKS


def round_int(x: float) -> int:
    """
    Округление минут до целого.
    Используется везде при расчёте плановых минут.
    """
    import math
    return math.floor(x + 0.5)
