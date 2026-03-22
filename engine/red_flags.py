from dataclasses import dataclass


@dataclass
class CheckinData:
    wellbeing: int        # 1=плохо, 2=тяжеловато, 3=нормально, 4=хорошо, 5=отлично
    sleep_quality: int    # 1=плохо, 2=нормально, 3=хорошо
    pain_level: int       # 1=нет, 2=немного, 3=есть
    pain_increases: bool | None = None  # None if pain_level == 1


def detect_red_flag(checkin: CheckinData) -> bool:
    """
    Red flag → only recovery allowed:
    1. Active pain (level 3)
    2. Pain escalates under load
    3. Very bad state: wellbeing == 1 (плохо) AND pain > 1
    """
    if checkin.pain_level == 3:
        return True
    if checkin.pain_increases is True:
        return True
    if checkin.wellbeing == 1 and checkin.pain_level > 1:
        return True
    return False
