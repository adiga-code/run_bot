from dataclasses import dataclass
from typing import Literal


FrequencyType = Literal["0_1", "2_3", "4plus"]
VolumeType = Literal["0", "to_10", "10_25", "25_50", "50plus"]
PainType = Literal["none", "little", "yes"]
PainIncreasesType = Literal["no", "yes", "not_sure"]
LocationType = Literal["home", "gym"]


@dataclass
class OnboardingAnswers:
    runs: bool                      # бегает ли вообще
    frequency: FrequencyType        # 0-1 / 2-3 / 4+ раза в неделю
    volume: VolumeType              # км/нед
    structure: bool                 # есть ли план/система
    had_break: bool                 # был ли перерыв
    pain: PainType                  # none / little / yes
    pain_increases: PainIncreasesType  # усиливается ли боль
    location: LocationType          # home / gym


def assign_level(answers: OnboardingAnswers) -> int:
    """
    Scoring-based level assignment (1-4).
    Level 5 (Performance) is assigned manually by the trainer only.

    Scoring:
      runs:      yes → +1
      frequency: 0-1 → 0, 2-3 → +1, 4+ → +2
      volume:    0 / to_10 → 0, 10_25 → +1, 25_50 → +2, 50plus → +3
      structure: yes → +1
      had_break: yes → -1
      pain:      little → -1 (yes = cap, not subtract)

    Hard constraints (applied after scoring):
      pain worsens   → level = 1
      not runs       → level = 1
      pain = yes     → level ≤ 2
      frequency 0-1  → level ≤ 2
      no structure   → level ≤ 3

    Score → level:
      0-1 → 1, 2-3 → 2, 4-5 → 3, 6+ → 4
    """
    # Hard stops regardless of score
    if not answers.runs:
        return 1
    if answers.pain_increases == "yes":
        return 1

    score = 1  # +1 for running at all

    score += {"0_1": 0, "2_3": 1, "4plus": 2}.get(answers.frequency, 0)
    score += {"0": 0, "to_10": 0, "10_25": 1, "25_50": 2, "50plus": 3}.get(answers.volume, 0)

    if answers.structure:
        score += 1
    if answers.had_break:
        score -= 1
    if answers.pain == "little":
        score -= 1

    # Score → base level
    if score <= 1:
        level = 1
    elif score <= 3:
        level = 2
    elif score <= 5:
        level = 3
    else:
        level = 4

    # Apply constraints
    if answers.pain == "yes" and level > 2:
        level = 2
    if answers.frequency == "0_1" and level > 2:
        level = 2
    if not answers.structure and level > 3:
        level = 3

    # Someone who already runs 2+ times/week is not a beginner — floor at 2
    if answers.runs and answers.frequency in ("2_3", "4plus") and level < 2:
        level = 2

    return level
