from dataclasses import dataclass
from typing import Literal

FrequencyType = Literal["not_at_all", "once", "2_3x", "4plus"]
VolumeType = Literal["none", "up_to_60", "60_to_120", "120plus"]
RegularityType = Literal["no_system", "sometimes", "regularly"]
BreakType = Literal["long_break", "had_break", "no_break"]
PainType = Literal["none", "little", "yes"]
PainIncreasesType = Literal["no", "yes", "not_sure"]
StrengthType = Literal["no", "sometimes", "regularly"]
LocationType = Literal["home", "gym"]


@dataclass
class OnboardingAnswers:
    frequency: FrequencyType
    volume: VolumeType
    regularity: RegularityType
    break_status: BreakType
    pain: PainType
    pain_increases: PainIncreasesType
    strength: StrengthType
    location: LocationType


def assign_level(answers: OnboardingAnswers) -> int:
    """
    Level 1 — Start:       doesn't run / has pain / long break / post-injury
    Level 2 — Return:      had a break / no system
    Level 3 — Base:        runs chaotically / some system
    Level 4 — Stability:   runs regularly, no pain, no break
    Level 5 — Performance: high-volume competitive runner (4+/week, 120+ min/week)
    """
    # Level 1: active pain, no running history, or very long break
    if answers.pain == "yes":
        return 1
    if answers.frequency == "not_at_all":
        return 1
    if answers.break_status == "long_break":
        return 1

    # Level 5: high-volume competitive runners
    if (
        answers.frequency == "4plus"
        and answers.volume == "120plus"
        and answers.regularity == "regularly"
        and answers.break_status == "no_break"
        and answers.pain == "none"
    ):
        return 5

    # Level 4: consistent + no break + no pain
    if (
        answers.frequency in ("2_3x", "4plus")
        and answers.regularity == "regularly"
        and answers.break_status == "no_break"
        and answers.pain == "none"
    ):
        return 4

    # Level 2: recent break or no system at all
    if answers.break_status == "had_break" or answers.regularity == "no_system":
        return 2

    # Level 3: everything else (some running, some system, minor issues)
    return 3
