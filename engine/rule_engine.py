from dataclasses import dataclass

from engine.red_flags import CheckinData, detect_red_flag
from engine.fatigue import RecentLogData, detect_cumulative_fatigue, detect_severe_fatigue, detect_persistent_pain


@dataclass
class WorkoutDecision:
    version: str           # base / light / recovery / rest
    reason: str            # human-readable reason (for logs/telemetry)
    red_flag: bool
    fatigue_reduction: bool


def decide_workout_version(
    checkin: CheckinData,
    recent_logs: list[RecentLogData],
    day_type: str,
    prev_day_type: str | None = None,
) -> WorkoutDecision:
    """
    Выбор версии тренировки по приоритетной системе (сверху вниз):

    0. День отдыха → rest

    🚨 КРАСНЫЕ ФЛАГИ (→ Recovery):
       - Боль «есть» (уровень 3)
       - Боль «немного» 2+ дня подряд (история)
       - Самочувствие плохо + стресс высокий

    1. Боль (приоритет 1):
       - боль = есть (3)  → Recovery
       - боль = немного (2) → Light

    2. Возврат после боли:
       - вчера была боль, сегодня нет → 1 день Light

    3. Самочувствие (приоритет 2):
       - самочувствие = плохо (1) → Light

    4. Сон и стресс (приоритет 3):
       - сон = плохо (1) ИЛИ стресс = высокий (3) → Light

    5. Накопленная усталость (история):
       - 3 тяжёлых дня → Recovery
       - 2 тяжёлых дня → Light

    6. Всё нормально → Base
    """
    # ── 0. День отдыха ────────────────────────────────────────────────────────
    if day_type == "rest":
        return WorkoutDecision(
            version="rest",
            reason="день отдыха по плану",
            red_flag=False,
            fatigue_reduction=False,
        )

    # ── 🚨 Красный флаг: боль 2+ дня подряд ─────────────────────────────────
    if detect_persistent_pain(recent_logs):
        return WorkoutDecision(
            version="recovery",
            reason="боль 2+ дня подряд — красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # ── 🚨 Красный флаг: боль есть (6-10) ────────────────────────────────────
    if checkin.pain_level == 3:
        return WorkoutDecision(
            version="recovery",
            reason="боль: есть (6–10) — красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # ── 🚨 Красный флаг: плохо + высокий стресс ──────────────────────────────
    if detect_red_flag(checkin):
        return WorkoutDecision(
            version="recovery",
            reason="плохое самочувствие + высокий стресс — красный флаг",
            red_flag=True,
            fatigue_reduction=False,
        )

    # ── Приоритет 1: боль немного (3-5) ──────────────────────────────────────
    if checkin.pain_level == 2:
        return WorkoutDecision(
            version="light",
            reason="боль: немного (3–5)",
            red_flag=False,
            fatigue_reduction=False,
        )

    # ── Возврат после боли: вчера болело → сегодня 1 день light ──────────────
    if recent_logs and recent_logs[-1].pain_level >= 2:
        return WorkoutDecision(
            version="light",
            reason="восстановление после боли — 1 день light",
            red_flag=False,
            fatigue_reduction=True,
        )

    # ── Приоритет 2: самочувствие плохо ──────────────────────────────────────
    if checkin.wellbeing == 1:
        return WorkoutDecision(
            version="light",
            reason="самочувствие: плохо",
            red_flag=False,
            fatigue_reduction=False,
        )

    # ── Приоритет 3: сон плохой или стресс высокий ───────────────────────────
    if checkin.sleep_quality == 1 or checkin.stress_level == 3:
        return WorkoutDecision(
            version="light",
            reason="плохой сон или высокий стресс",
            red_flag=False,
            fatigue_reduction=False,
        )

    # ── Накопленная усталость (история) ──────────────────────────────────────
    if detect_severe_fatigue(recent_logs):
        return WorkoutDecision(
            version="recovery",
            reason="3 тяжёлых дня подряд — принудительное восстановление",
            red_flag=False,
            fatigue_reduction=True,
        )

    if detect_cumulative_fatigue(recent_logs):
        return WorkoutDecision(
            version="light",
            reason="накопленная усталость (2+ тяжёлых дня) — снижение нагрузки",
            red_flag=False,
            fatigue_reduction=True,
        )

    # ── Всё нормально → Base ─────────────────────────────────────────────────
    return WorkoutDecision(
        version="base",
        reason="хорошее самочувствие",
        red_flag=False,
        fatigue_reduction=False,
    )
