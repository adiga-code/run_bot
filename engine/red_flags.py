from dataclasses import dataclass


@dataclass
class CheckinData:
    wellbeing: int        # 1=плохо, 2=нормально, 3=отлично
    sleep_quality: int    # 1=плохо, 2=средне, 3=хорошо
    pain_level: int       # 1=нет (0-2), 2=немного (3-5), 3=есть (6-10)
    stress_level: int = 1  # 1=низкий, 2=средний, 3=высокий
    # Поле сохраняется в БД для совместимости, но в новом чек-ине не используется
    # (pain_level=3 уже означает боль усиливается / мешает движению)
    pain_increases: bool | None = None


def detect_red_flag(checkin: CheckinData) -> bool:
    """
    Red flag → только Recovery:
    1. Активная боль (уровень 3: есть, 6-10)
    2. Очень плохое состояние: самочувствие = плохо AND стресс = высокий
    """
    if checkin.pain_level == 3:
        return True
    if checkin.wellbeing == 1 and checkin.stress_level == 3:
        return True
    return False
