from dataclasses import dataclass

from engine.red_flags import CheckinData, detect_red_flag
from engine.fatigue import RecentLogData, detect_cumulative_fatigue, detect_severe_fatigue, detect_persistent_pain


@dataclass
class WorkoutDecision:
    version: str           # base / light / recovery / rest
    reason: str            # human-readable reason (for logs/telemetry)
    red_flag: bool
    fatigue_reduction: bool


def _score_from_checkin(checkin: CheckinData) -> tuple[int, str | None]:
    """
    Compute a fatigue score from checkin data.
    Returns (score, early_return_version) where early_return_version is set
    when an immediate override is triggered (e.g. pain == 3).
    """
    score = 0

    # Wellbeing
    if checkin.wellbeing == 2:  # тяжеловато
        score += 1
    elif checkin.wellbeing == 1:  # плохо
        score += 2

    # Sleep
    if checkin.sleep_quality == 1:  # плохо
        score += 1

    # Pain — immediate recovery override
    if checkin.pain_level == 3:  # есть
        return score, "recovery"
    if checkin.pain_level == 2:  # немного
        score += 2

    # Stress
    if checkin.stress_level == 2:  # умеренный
        score += 1
    elif checkin.stress_level == 3:  # сильный
        score += 2

    return score, None


def decide_workout_version(
    checkin: CheckinData,
    recent_logs: list[RecentLogData],
    day_type: str,
    prev_day_type: str | None = None,
) -> WorkoutDecision:
    """
    Selects workout version using a scoring formula with red-flag overrides
    and cumulative fatigue detection.

    Red flags (override everything → recovery):
      - pain == 3 (есть)
      - pain_increases == True
      - wellbeing == 1 AND stress >= 2

    Scoring:
      wellbeing 2 → +1, wellbeing 1 → +2
      sleep 1    → +1
      pain 3     → immediate recovery (no score path)
      pain 2     → +2
      stress 2   → +1, stress 3 → +2

      score <= 1  → base
      score <= 3  → light
      score >= 4  → recovery

    After-strength cap:
      If prev_day_type == "strength" and version would be "base" → cap at "light"

    Cumulative fatigue (2 consecutive tough days → light minimum, 3 → recovery):
      Tough day = wellbeing <= 2 OR stress >= 2 OR completion_status in (partial, skipped)
    """
    if day_type == "rest":
        return WorkoutDecision(
            version="rest",
            reason="день отдыха по плану",
            red_flag=False,
            fatigue_reduction=False,
        )

    # ── Red flag overrides ────────────────────────────────────────────────────

    # pain == 3 → immediate recovery
    if checkin.pain_level == 3:
        return WorkoutDecision(
            version="recovery",
            reason="боль: уровень 3 (есть) — красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # pain_increases → recovery
    if checkin.pain_increases is True:
        return WorkoutDecision(
            version="recovery",
            reason="боль усиливается при нагрузке — красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # wellbeing == 1 AND stress >= 2 → recovery
    if checkin.wellbeing == 1 and checkin.stress_level >= 2:
        return WorkoutDecision(
            version="recovery",
            reason="плохое самочувствие + стресс — красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # Generic detect_red_flag (handles any remaining combinations)
    if detect_red_flag(checkin):
        return WorkoutDecision(
            version="recovery",
            reason="красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # ── Scoring ───────────────────────────────────────────────────────────────

    score, _ = _score_from_checkin(checkin)

    # today_is_good: wellbeing is at least normal AND no pain today.
    # When true: cap score-based recovery at light, and skip historical overrides.
    today_is_good = checkin.wellbeing >= 3 and checkin.pain_level == 1

    if score <= 1:
        version = "base"
        reason = "хорошее самочувствие"
    elif score <= 3:
        version = "light"
        reason = f"умеренная нагрузка (score={score})"
    else:
        if today_is_good:
            # Athlete feels ok today — bad sleep or stress alone doesn't justify full recovery.
            # Cap at light so the system doesn't over-react to a single bad metric.
            version = "light"
            reason = f"сон/стресс снизили нагрузку, но самочувствие нормальное (score={score})"
        else:
            version = "recovery"
            reason = f"высокий балл усталости (score={score})"

    # ── Cumulative fatigue check ───────────────────────────────────────────────

    fatigue_reduction = False

    if version != "recovery":
        # Persistent pain (2+ days): pull Base down to Light as a safety measure.
        # Never escalates Light → Recovery — "немного боли" alone is not enough
        # for recovery; only acute pain (level 3) or very bad wellbeing triggers that.
        if detect_persistent_pain(recent_logs) and version == "base":
            version = "light"
            reason = "боль 2+ дня подряд — снижение нагрузки до light"
            fatigue_reduction = True
        elif not today_is_good:
            # Historical fatigue overrides only apply when today also shows
            # some signs of fatigue. If today is fine, trust today's state.
            if detect_severe_fatigue(recent_logs):
                version = "recovery"
                reason = "3 тяжёлых дня подряд — принудительное восстановление"
                fatigue_reduction = True
            elif detect_cumulative_fatigue(recent_logs):
                if version == "base":
                    version = "light"
                    reason = "накопленная усталость (2+ тяжёлых дня) — снижение нагрузки"
                    fatigue_reduction = True

    # ── After-strength cap ────────────────────────────────────────────────────
    # Applies only when there is at least some fatigue signal (score > 0).
    # If the athlete feels great (score == 0, no fatigue), we trust that and
    # keep Base even after a strength day.

    if (
        version == "base"
        and prev_day_type == "strength"
        and not fatigue_reduction
        and score > 0
    ):
        version = "light"
        reason = "день после силовой + есть признаки усталости — нагрузка ограничена до light"

    return WorkoutDecision(
        version=version,
        reason=reason,
        red_flag=False,
        fatigue_reduction=fatigue_reduction,
    )
