from dataclasses import dataclass

from engine.red_flags import CheckinData, detect_red_flag
from engine.fatigue import RecentLogData, detect_cumulative_fatigue


@dataclass
class WorkoutDecision:
    version: str           # base / light / recovery / rest
    reason: str            # human-readable reason (for logs/telemetry)
    red_flag: bool
    fatigue_reduction: bool
    score: int = 0         # stress-score that led to this decision


def _calc_score(checkin: CheckinData) -> int:
    """
    Stress-score based on the client's formula:
      wellbeing тяжеловато(2) → +1
      wellbeing плохо(1)      → +2
      sleep плохо(1)          → +1
      pain немного(2)         → +2
      stress умеренный(2)     → +1
      stress сильный(3)       → +2

    pain==3 and pain_increases are handled as red flags before score calc.
    """
    score = 0
    if checkin.wellbeing == 1:
        score += 2
    elif checkin.wellbeing == 2:
        score += 1

    if checkin.sleep_quality == 1:
        score += 1

    if checkin.pain_level == 2:
        score += 2

    if checkin.stress_level == 2:
        score += 1
    elif checkin.stress_level == 3:
        score += 2

    return score


def decide_workout_version(
    checkin: CheckinData,
    recent_logs: list[RecentLogData],
    day_type: str,
    prev_day_type: str | None = None,
) -> WorkoutDecision:
    """
    Selects workout version using score-based logic from the client spec.

    Priority chain:
      1. Rest day → always rest
      2. Red flag (pain==3, escalating pain, или bad+high stress) → recovery
      3. Score calculation → base/light/recovery
      4. Cumulative fatigue (2+ tough days) → force score ≥ 2 (at least light)
      5. After-strength constraint: prev_day_type==strength + run → cap at light
    """
    if day_type == "rest":
        return WorkoutDecision(
            version="rest",
            reason="день отдыха по плану",
            red_flag=False,
            fatigue_reduction=False,
            score=0,
        )

    if detect_red_flag(checkin):
        return WorkoutDecision(
            version="recovery",
            reason="красный флаг: боль, нарастающая боль или сильный стресс + плохое состояние",
            red_flag=True,
            fatigue_reduction=False,
            score=99,
        )

    score = _calc_score(checkin)

    # Cumulative fatigue: ensure at least light
    fatigue = detect_cumulative_fatigue(recent_logs)
    if fatigue and score < 2:
        score = 2

    # After-strength constraint: no heavy run after strength day
    after_strength = (prev_day_type == "strength" and day_type == "run")
    if after_strength and score < 2:
        score = 2

    # Map score to version
    if score <= 1:
        version = "base"
    elif score <= 3:
        version = "light"
    else:
        version = "recovery"

    reason_parts = []
    if fatigue:
        reason_parts.append("накопленная усталость")
    if after_strength:
        reason_parts.append("день после силовой")
    if score == 0:
        reason_parts.append("хорошее самочувствие")
    elif score == 1:
        reason_parts.append(f"лёгкий дискомфорт (балл {score})")
    else:
        reason_parts.append(f"стресс-балл {score}")

    return WorkoutDecision(
        version=version,
        reason=", ".join(reason_parts),
        red_flag=False,
        fatigue_reduction=fatigue,
        score=score,
    )
