from datetime import date, datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ══════════════════════════════════════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone_offset: Mapped[int] = mapped_column(Integer, default=3)  # UTC+X

    # ── Program state (old) ───────────────────────────────────────────────────
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)        # 1-5
    strength_format: Mapped[str | None] = mapped_column(String(10), nullable=True)  # home/gym
    program_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # deprecated — used for old 28-day users only
    week_repeat_count: Mapped[int] = mapped_column(Integer, default=0)
    extended_week5: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Reminders ─────────────────────────────────────────────────────────────
    morning_reminder_hour: Mapped[int] = mapped_column(Integer, default=8)
    evening_reminder_hour: Mapped[int] = mapped_column(Integer, default=20)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Profile (Блок 1) ──────────────────────────────────────────────────────
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)    # m / f

    # ── Onboarding answers (raw) ──────────────────────────────────────────────
    q_goal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    q_runs: Mapped[str | None] = mapped_column(String(20), nullable=True)    # no/irregular/regular
    q_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_volume: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_longest_run: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_structure: Mapped[str | None] = mapped_column(String(10), nullable=True)   # yes/no
    q_experience: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_break: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_break_duration: Mapped[str | None] = mapped_column(String(20), nullable=True)  # no/to_1m/1_3m/3_6m/6plus
    q_run_feel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_pain: Mapped[str | None] = mapped_column(String(20), nullable=True)    # none/little/yes
    q_pain_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    q_pain_increases: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_injury_history: Mapped[str | None] = mapped_column(String(10), nullable=True)  # yes/no
    q_other_sports: Mapped[str | None] = mapped_column(String(200), nullable=True)
    q_strength_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_self_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_distance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_race_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    q_regularity: Mapped[str | None] = mapped_column(String(20), nullable=True)   # legacy
    q_strength: Mapped[str | None] = mapped_column(String(20), nullable=True)     # legacy
    # NEW — онбординг v2
    q_continuous_run_test: Mapped[str | None] = mapped_column(String(10), nullable=True)  # yes/no/unsure
    # Блок гаджеты (не влияет на decision-логику, только сбор данных)
    q_gadget: Mapped[str | None] = mapped_column(String(10), nullable=True)        # yes / no
    q_gadget_types: Mapped[str | None] = mapped_column(String(200), nullable=True)  # whoop,garmin,oura,apple_watch,polar,fitbit,other
    q_gadget_sharing: Mapped[str | None] = mapped_column(String(10), nullable=True) # yes / no / later

    # ── NEW: доступные дни и объём ────────────────────────────────────────────
    available_weekdays: Mapped[str | None] = mapped_column(String(20), nullable=True)   # "1,3,5"
    weekly_target_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_volume_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_successful_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Referral tracking
    referral_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── NEW: период и цикл ────────────────────────────────────────────────────
    # base_in / base / preparatory / specialized / recovery_period
    current_period: Mapped[str | None] = mapped_column(String(30), nullable=True)
    period_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_week_number: Mapped[int] = mapped_column(Integer, default=1)
    cycle_number: Mapped[int] = mapped_column(Integer, default=1)
    cycle_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    program_week_number: Mapped[int] = mapped_column(Integer, default=1)

    # ── NEW: счётчики прогрессии ──────────────────────────────────────────────
    growth_streak: Mapped[int] = mapped_column(Integer, default=0)
    weeks_since_recovery: Mapped[int] = mapped_column(Integer, default=0)

    # ── NEW: red flag / откат ─────────────────────────────────────────────────
    red_flag_active: Mapped[bool] = mapped_column(Boolean, default=False)
    red_flag_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    red_flag_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── NEW: точка входа и цель ───────────────────────────────────────────────
    has_goal_race: Mapped[bool] = mapped_column(Boolean, default=False)
    entry_point: Mapped[str | None] = mapped_column(String(20), nullable=True)  # base_in / base

    # ── NEW: return-mode (после перерыва) ─────────────────────────────────────
    injury_return_active: Mapped[bool] = mapped_column(Boolean, default=False)
    target_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    return_mode_started_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── NEW: L3 regular — recovery period ────────────────────────────────────
    in_macrocycle_recovery: Mapped[bool] = mapped_column(Boolean, default=False)
    macrocycle_recovery_week: Mapped[int] = mapped_column(Integer, default=0)
    macrocycle_peak_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── NEW: L1 long stage ────────────────────────────────────────────────────
    l1_long_independent: Mapped[bool] = mapped_column(Boolean, default=False)
    l1_no_pain_streak_weeks: Mapped[int] = mapped_column(Integer, default=0)
    l1_easy_reached_40min: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Access & lifecycle ────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="active")
    role: Mapped[str] = mapped_column(String(20), default="athlete")  # athlete / admin (reserved)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    session_logs: Mapped[list["SessionLog"]] = relationship(back_populates="user")
    week_plans: Mapped[list["WeekPlan"]] = relationship(back_populates="user")


# ══════════════════════════════════════════════════════════════════════════════
# WORKOUT (старая таблица — для старых 28-дневных пользователей)
# ══════════════════════════════════════════════════════════════════════════════

class Workout(Base):
    """Old: one row = one version of one workout for one level on one day."""
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)          # 1-28
    day_type: Mapped[str] = mapped_column(String(20))  # run/strength/recovery/rest
    version: Mapped[str] = mapped_column(String(20))   # base/light/recovery
    strength_format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    short_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    micro_learning: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


# ══════════════════════════════════════════════════════════════════════════════
# WORKOUT TEMPLATE (новая таблица — для новой программной логики)
# ══════════════════════════════════════════════════════════════════════════════

class WorkoutTemplate(Base):
    """
    Библиотека шаблонов тренировок для новой динамической логики.
    Без жёсткой привязки к дню 1-28.
    Текст содержит плейсхолдеры: {minutes}, {warmup_minutes} и т.п.
    """
    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[int] = mapped_column(Integer)                         # 1-4
    day_type: Mapped[str] = mapped_column(String(20))                   # run/strength/recovery/rest/mobility
    run_subtype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # easy/aerobic/recovery_run/long/tempo/intervals/run_walk
    version: Mapped[str] = mapped_column(String(20))                    # base/light/recovery
    intensity_kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # null / z3_inclusions / tempo / intervals
    period: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # base_in/base/preparatory/null (универсал)
    strength_format: Mapped[str | None] = mapped_column(String(10), nullable=True)  # gym/home/null

    title: Mapped[str] = mapped_column(String(200))
    short_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(Text)                             # с плейсхолдерами {minutes}
    micro_learning: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


# ══════════════════════════════════════════════════════════════════════════════
# WEEK PLAN
# ══════════════════════════════════════════════════════════════════════════════

class WeekPlan(Base):
    """Недельный план для одного пользователя."""
    __tablename__ = "week_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer)                   # сквозная нумерация
    cycle_number: Mapped[int] = mapped_column(Integer, default=1)
    period: Mapped[str] = mapped_column(String(30))
    # base_in/base/preparatory/specialized/recovery_period
    period_week_number: Mapped[int] = mapped_column(Integer, default=1)

    start_date: Mapped[date] = mapped_column(Date)                      # понедельник
    end_date: Mapped[date] = mapped_column(Date)                        # воскресенье

    weekly_target_minutes: Mapped[int] = mapped_column(Integer)         # плановый объём БЕГА
    is_recovery_week: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rollback_week: Mapped[bool] = mapped_column(Boolean, default=False)

    # Итоги (заполняется при закрытии недели)
    actual_running_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    keys_completed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    growth_eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    no_growth_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="week_plans")
    days: Mapped[list["DayPlan"]] = relationship(back_populates="week_plan",
                                                  cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_week_plans_user_start", "user_id", "start_date"),
        Index("ix_week_plans_user_closed", "user_id", "closed_at"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# DAY PLAN
# ══════════════════════════════════════════════════════════════════════════════

class DayPlan(Base):
    """План конкретного дня внутри недели."""
    __tablename__ = "day_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("week_plans.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer)                   # 1=Пн .. 7=Вс

    day_type: Mapped[str] = mapped_column(String(20))
    # run / strength / recovery / rest / mobility
    run_subtype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # easy/aerobic/recovery_run/long/tempo/intervals/run_walk/null
    planned_minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # null / z3_inclusions / tempo / intervals

    is_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_key_completed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # null до закрытия дня

    # Связь с реальным выполнением (заполняется при наступлении дня)
    session_log_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("session_logs.id"), nullable=True)

    # Relationships
    week_plan: Mapped["WeekPlan"] = relationship(back_populates="days")

    __table_args__ = (
        UniqueConstraint("week_plan_id", "day_of_week", name="uq_day_plan_week_day"),
        Index("ix_day_plans_week_key", "week_plan_id", "is_key"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# SESSION LOG
# ══════════════════════════════════════════════════════════════════════════════

class SessionLog(Base):
    """One row = one program day for one user."""
    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    date: Mapped[date] = mapped_column(Date)
    # day_index deprecated — kept for old 28-day users
    day_index: Mapped[int] = mapped_column(Integer, default=0)

    # ── NEW: связь с новыми планами ────────────────────────────────────────────
    week_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("week_plans.id"), nullable=True)
    day_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("day_plans.id"), nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 1-7
    planned_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Утренний чек-ин ───────────────────────────────────────────────────────
    # wellbeing:    1=плохо, 2=тяжеловато, 3=нормально, 4=отлично
    # sleep_quality: 1=плохо, 2=средне, 3=хорошо
    # pain_level:   1=нет (0-2/10), 2=немного (3-5/10), 3=есть (6-10/10)
    # stress_level: 1=низкий, 2=средний, 3=высокий
    wellbeing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_increases: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # legacy
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Назначенная тренировка ────────────────────────────────────────────────
    assigned_workout_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("workouts.id"), nullable=True)
    assigned_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # base / light / recovery / rest

    # ── Вечерний маркинг ──────────────────────────────────────────────────────
    # completion_status: "done" / "skipped"
    # ("partial" — deprecated, старые записи сохраняются, новые не пишутся)
    completion_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    effort_level: Mapped[int | None] = mapped_column(Integer, nullable=True)     # 1-5
    completion_pain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── NEW: coach override ───────────────────────────────────────────────────
    coach_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    override_workout_template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workout_templates.id"), nullable=True
    )
    override_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── NEW: absence-flow аналитика ───────────────────────────────────────────
    absence_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # tired/sick/no_time/motivation/weather/other
    absence_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    absence_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── NEW: re-checkin tracking ──────────────────────────────────────────────
    recheckin_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checkin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Engine flags (telemetry) ──────────────────────────────────────────────
    red_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    # fatigue_reduction deprecated — не пишем новые, старые сохраняются
    fatigue_reduction: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Reminder tracking ─────────────────────────────────────────────────────
    morning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    evening_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    checkin_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Manual approval flow ──────────────────────────────────────────────────
    approval_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    checkin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="session_logs")
    workout: Mapped["Workout | None"] = relationship()


class ReferralLink(Base):
    __tablename__ = "referral_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)



class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    date_label: Mapped[str] = mapped_column(String(100), nullable=False)       # e.g. "17 мая"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    channel_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    registrations: Mapped[list["EventRegistration"]] = relationship(back_populates="event")


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tg_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    event: Mapped["Event"] = relationship(back_populates="registrations")


# ══════════════════════════════════════════════════════════════════════════════
# WHITELIST
# ══════════════════════════════════════════════════════════════════════════════

class WhitelistEntry(Base):
    __tablename__ = "whitelist"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    added_by: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
