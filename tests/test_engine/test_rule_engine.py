import pytest
from engine.red_flags import CheckinData
from engine.fatigue import RecentLogData
from engine.rule_engine import decide_workout_version


# ── Fixtures ──────────────────────────────────────────────────────────────────

def good_checkin() -> CheckinData:
    """Отличное состояние: всё хорошо."""
    return CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=1)


def ok_checkin() -> CheckinData:
    """Нормальное состояние: нет явных триггеров."""
    return CheckinData(wellbeing=2, sleep_quality=2, pain_level=1, stress_level=1)


def bad_checkin() -> CheckinData:
    """pain_level=3 → красный флаг."""
    return CheckinData(wellbeing=1, sleep_quality=1, pain_level=3, stress_level=1)


def easy_logs(n: int = 3) -> list[RecentLogData]:
    """3 лёгких дня — нет усталости."""
    return [RecentLogData(effort_level=2, sleep_quality=3, completion_status="done", pain_level=1) for _ in range(n)]


def pain_logs(n: int = 2) -> list[RecentLogData]:
    """Дни с болью уровня 2 (немного) — для теста persist_pain."""
    return [RecentLogData(effort_level=2, sleep_quality=3, completion_status="done", pain_level=2) for _ in range(n)]


def tough_logs(n: int = 3) -> list[RecentLogData]:
    """3 тяжёлых дня (плохой сон): severe_fatigue → recovery."""
    return [RecentLogData(effort_level=5, sleep_quality=1, completion_status="done", pain_level=1) for _ in range(n)]


def mixed_logs_2_of_3() -> list[RecentLogData]:
    """2 из 3 тяжёлых (по статусу): cumulative_fatigue → light."""
    return [
        RecentLogData(effort_level=2, sleep_quality=3, completion_status="done", pain_level=1),
        RecentLogData(effort_level=2, sleep_quality=3, completion_status="skipped", pain_level=1),
        RecentLogData(effort_level=2, sleep_quality=3, completion_status="skipped", pain_level=1),
    ]


# ── День отдыха ───────────────────────────────────────────────────────────────

def test_rest_day_always_rest():
    decision = decide_workout_version(bad_checkin(), tough_logs(), day_type="rest")
    assert decision.version == "rest"
    assert decision.red_flag is False


# ── Красные флаги → recovery ──────────────────────────────────────────────────

def test_pain3_gives_recovery():
    """Боль «есть» (уровень 3) → Recovery, красный флаг."""
    decision = decide_workout_version(bad_checkin(), easy_logs(), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True
    assert decision.fatigue_reduction is False


def test_persistent_pain_gives_recovery():
    """Боль «немного» 2 дня подряд → Recovery, красный флаг."""
    checkin = good_checkin()  # сегодня всё хорошо — боль прошла
    decision = decide_workout_version(checkin, pain_logs(2), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True


def test_red_flag_wellbeing_and_high_stress():
    """Самочувствие плохо + стресс высокий → Recovery."""
    checkin = CheckinData(wellbeing=1, sleep_quality=2, pain_level=1, stress_level=3)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True


def test_red_flag_overrides_everything():
    """Красный флаг имеет наивысший приоритет."""
    decision = decide_workout_version(bad_checkin(), tough_logs(), day_type="run")
    assert decision.version == "recovery"
    assert decision.red_flag is True


# ── Приоритет 1: боль немного → light ────────────────────────────────────────

def test_pain2_gives_light():
    """Боль «немного» (уровень 2) → Light."""
    checkin = CheckinData(wellbeing=3, sleep_quality=3, pain_level=2, stress_level=1)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"
    assert decision.red_flag is False


# ── Возврат после боли → light ────────────────────────────────────────────────

def test_recovery_after_pain_gives_light():
    """Вчера была боль, сегодня нет → 1 день Light."""
    checkin = good_checkin()
    logs = [
        RecentLogData(effort_level=2, sleep_quality=3, completion_status="done", pain_level=1),
        RecentLogData(effort_level=2, sleep_quality=3, completion_status="done", pain_level=2),  # вчера боль
    ]
    decision = decide_workout_version(checkin, logs, day_type="run")
    assert decision.version == "light"
    assert decision.fatigue_reduction is True


# ── Приоритет 2: самочувствие плохо → light ──────────────────────────────────

def test_bad_wellbeing_alone_gives_light():
    """Самочувствие плохо → Light."""
    checkin = CheckinData(wellbeing=1, sleep_quality=3, pain_level=1, stress_level=1)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"
    assert decision.red_flag is False
    assert decision.fatigue_reduction is False


# ── Приоритет 3: сон / стресс → light ────────────────────────────────────────

def test_bad_sleep_gives_light():
    """Плохой сон → Light (по новой логике)."""
    checkin = CheckinData(wellbeing=3, sleep_quality=1, pain_level=1, stress_level=1)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"


def test_high_stress_gives_light():
    """Высокий стресс (3) → Light."""
    checkin = CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=3)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "light"


def test_medium_stress_alone_gives_base():
    """Средний стресс (2) без других триггеров → Base."""
    checkin = CheckinData(wellbeing=3, sleep_quality=3, pain_level=1, stress_level=2)
    decision = decide_workout_version(checkin, easy_logs(), day_type="run")
    assert decision.version == "base"


# ── Накопленная усталость (история) ──────────────────────────────────────────

def test_severe_fatigue_gives_recovery():
    """3 тяжёлых дня подряд → Recovery."""
    decision = decide_workout_version(good_checkin(), tough_logs(3), day_type="run")
    assert decision.version == "recovery"
    assert decision.fatigue_reduction is True
    assert decision.red_flag is False


def test_cumulative_fatigue_gives_light():
    """2 из 3 дней тяжёлые → Light."""
    decision = decide_workout_version(good_checkin(), mixed_logs_2_of_3(), day_type="run")
    assert decision.version == "light"
    assert decision.fatigue_reduction is True


# ── Хорошее состояние → base ──────────────────────────────────────────────────

def test_good_state_gives_base():
    decision = decide_workout_version(good_checkin(), easy_logs(), day_type="run")
    assert decision.version == "base"
    assert decision.red_flag is False
    assert decision.fatigue_reduction is False


def test_ok_state_gives_base():
    decision = decide_workout_version(ok_checkin(), easy_logs(), day_type="strength")
    assert decision.version == "base"


def test_recovery_day_type_with_good_state():
    """day_type=recovery + хорошее состояние → base (версия recovery-тренировки)."""
    decision = decide_workout_version(good_checkin(), easy_logs(), day_type="recovery")
    assert decision.version == "base"
