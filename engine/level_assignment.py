from dataclasses import dataclass
from typing import Literal


FrequencyType = Literal["0_1", "2_3", "4plus"]
VolumeType = Literal["0", "to_10", "10_25", "25_50", "50plus"]
PainType = Literal["none", "little", "yes"]
PainIncreasesType = Literal["no", "yes", "not_sure"]
LocationType = Literal["home", "gym"]
BreakDurationType = Literal["no", "to_1m", "1_3m", "3_6m", "6plus"]
ContinuousRunType = Literal["yes", "no", "unsure"]


@dataclass
class OnboardingAnswers:
    runs: bool                               # бегает ли вообще
    frequency: FrequencyType                 # 0_1 / 2_3 / 4plus раза в неделю
    volume: VolumeType                       # км/нед
    structure: bool                          # есть ли план/система
    had_break: bool                          # был ли перерыв
    pain: PainType                           # none / little / yes
    pain_increases: PainIncreasesType        # усиливается ли боль
    location: LocationType                   # home / gym

    # Расширенные поля (новый онбординг v2)
    q_break_duration: BreakDurationType = "no"
    q_longest_run: str = ""                  # 0/to_5/5_15/15_30/30_60/60plus
    q_continuous_run_test: ContinuousRunType | None = None  # yes/no/unsure
    q_goal: str = ""                         # race/distance/health/improve/…


# ══════════════════════════════════════════════════════════════════════════════
# assign_level — основной скоринг (без изменений)
# ══════════════════════════════════════════════════════════════════════════════

def assign_level(answers: OnboardingAnswers) -> int:
    """
    Scoring-based level assignment (1-4).
    Level 5 (Performance) is assigned manually by the trainer only.

    Scoring:
      runs:      yes → +1
      frequency: 0-1 → 0, 2-3 → +1, 4+ → +2
      volume:    0/to_10 → 0, 10_25 → +1, 25_50 → +2, 50plus → +3
      structure: yes → +1
      had_break: yes → -1
      pain:      little → -1

    Hard stops:
      pain_increases == yes    → level = 1
      not runs                 → level = 1
      pain == yes              → level ≤ 2
      frequency == 0_1         → level ≤ 2
      not structure            → level ≤ 3
    """
    if not answers.runs:
        return 1
    if answers.pain_increases == "yes":
        return 1

    score = 1  # +1 за то, что бегает

    score += {"0_1": 0, "2_3": 1, "4plus": 2}.get(answers.frequency, 0)
    score += {"0": 0, "to_10": 0, "10_25": 1, "25_50": 2, "50plus": 3}.get(answers.volume, 0)

    if answers.structure:
        score += 1
    if answers.had_break:
        score -= 1
    if answers.pain == "little":
        score -= 1

    if score <= 1:
        level = 1
    elif score <= 3:
        level = 2
    elif score <= 5:
        level = 3
    else:
        level = 4

    # Hard constraints
    if answers.pain == "yes" and level > 2:
        level = 2
    if answers.frequency == "0_1" and level > 2:
        level = 2
    if not answers.structure and level > 3:
        level = 3

    # Пол‑уровень: регулярно бегает → не ниже 2
    if answers.runs and answers.frequency in ("2_3", "4plus") and level < 2:
        level = 2

    return level


# ══════════════════════════════════════════════════════════════════════════════
# route_to_program
# ══════════════════════════════════════════════════════════════════════════════

def route_to_program(level: int) -> Literal["new", "manual"]:
    """
    Определяет, какая система ведёт пользователя.
    L1-L3 → новая программная логика.
    L4-L5 → manual (тренер ведёт вручную).
    """
    if level in (1, 2, 3):
        return "new"
    return "manual"


# ══════════════════════════════════════════════════════════════════════════════
# assign_entry_point
# ══════════════════════════════════════════════════════════════════════════════

def assign_entry_point(level: int, answers: OnboardingAnswers) -> str:
    """
    Возвращает 'base_in' или 'base'.
    Для L2/L3 всегда 'base'.
    Для L1 применяет приоритетные правила сверху вниз.
    """
    if level >= 2:
        return "base"

    # Hard-стоп 1: вообще не бегает
    if not answers.runs:
        return "base_in"

    # Hard-стоп 2: длительный перерыв (3+ мес)
    if answers.q_break_duration in ("3_6m", "6plus"):
        return "base_in"

    # Hard-стоп 3: самые короткие пробежки
    if answers.q_longest_run in ("0", "to_5"):
        return "base_in"

    # Прямой тест из онбординга
    if answers.q_continuous_run_test == "yes":
        return "base"
    if answers.q_continuous_run_test == "no":
        return "base_in"
    # q_continuous_run_test == "unsure" или None → fallback

    # Fallback по q_longest_run
    if answers.q_longest_run in ("5_15",):
        return "base_in"
    if answers.q_longest_run in ("15_30", "30_60", "60plus"):
        return "base"

    return "base_in"  # безопасный дефолт


# ══════════════════════════════════════════════════════════════════════════════
# detect_after_break_mode
# ══════════════════════════════════════════════════════════════════════════════

def detect_after_break_mode(level: int, answers: OnboardingAnswers) -> bool:
    """
    Был ли длительный перерыв у L2/L3 → return-mode (injury_return_active=True).
    Для L1 return-mode не нужен (там base_in всё покрывает).
    """
    if level < 2:
        return False
    return answers.q_break_duration in ("3_6m", "6plus")


# ══════════════════════════════════════════════════════════════════════════════
# assign_starting_volume
# ══════════════════════════════════════════════════════════════════════════════

def assign_starting_volume(level: int, entry_point: str, injury_return: bool = False) -> int:
    """
    Стартовый объём (мин/нед) — нижняя граница диапазона уровня.
    """
    from engine.constants import get_level_start_volume
    return get_level_start_volume(level, entry_point, injury_return)


# ══════════════════════════════════════════════════════════════════════════════
# assign_initial_period
# ══════════════════════════════════════════════════════════════════════════════

def assign_initial_period(level: int, entry_point: str) -> str:
    """
    Первый период программы для пользователя.
    """
    if level == 1:
        return entry_point  # "base_in" или "base"
    # L2, L3 (включая after break) — всегда начинают с base
    return "base"


# ══════════════════════════════════════════════════════════════════════════════
# has_goal_race
# ══════════════════════════════════════════════════════════════════════════════

def has_goal_race(answers: OnboardingAnswers) -> bool:
    """
    Пользователь поставил цель — пробежать забег или дистанцию.
    Нужно для перехода L1 base → specialized.
    """
    return answers.q_goal in ("race", "distance")
