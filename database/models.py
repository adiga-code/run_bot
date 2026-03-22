from datetime import date, datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone_offset: Mapped[int] = mapped_column(Integer, default=3)  # UTC+X

    # Program state
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-4
    strength_format: Mapped[str | None] = mapped_column(String(10), nullable=True)  # home/gym
    program_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    week_repeat_count: Mapped[int] = mapped_column(Integer, default=0)  # weeks repeated

    # Reminders (local hour, 0-23)
    morning_reminder_hour: Mapped[int] = mapped_column(Integer, default=8)
    evening_reminder_hour: Mapped[int] = mapped_column(Integer, default=20)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Onboarding answers (raw values, stored for reference)
    q_runs: Mapped[str | None] = mapped_column(String(10), nullable=True)        # yes / no
    q_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_volume: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_structure: Mapped[str | None] = mapped_column(String(10), nullable=True)   # yes / no
    q_regularity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # kept for legacy
    q_break: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_pain: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_pain_increases: Mapped[str | None] = mapped_column(String(20), nullable=True)
    q_strength: Mapped[str | None] = mapped_column(String(20), nullable=True)    # kept for legacy

    # Access & lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    # pending = ждёт подтверждения тренера; active = программа запущена
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="active")
    role: Mapped[str] = mapped_column(String(20), default="athlete")  # athlete / admin (reserved)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session_logs: Mapped[list["SessionLog"]] = relationship(back_populates="user")


class Workout(Base):
    """One row = one version of one workout for one level on one day."""
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[int] = mapped_column(Integer)          # 1-4
    day: Mapped[int] = mapped_column(Integer)            # 1-28
    day_type: Mapped[str] = mapped_column(String(20))    # run / strength / recovery / rest
    version: Mapped[str] = mapped_column(String(20))     # base / light / recovery
    strength_format: Mapped[str | None] = mapped_column(String(10), nullable=True)  # gym/home/null
    title: Mapped[str] = mapped_column(String(200))
    short_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    micro_learning: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


class SessionLog(Base):
    """One row = one program day for one user."""
    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    date: Mapped[date] = mapped_column(Date)
    day_index: Mapped[int] = mapped_column(Integer)  # 1-28

    # Morning check-in
    # wellbeing: 1=плохо, 2=тяжеловато, 3=нормально, 4=отлично
    # sleep_quality: 1=плохо, 2=нормально, 3=хорошо
    # pain_level: 1=нет, 2=немного, 3=есть
    # stress_level: 1=нет, 2=умеренный, 3=сильный
    wellbeing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_increases: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Assigned workout after rule engine decision
    assigned_workout_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("workouts.id"), nullable=True)
    assigned_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Completion (filled in the evening)
    completion_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # done/partial/skipped
    effort_level: Mapped[int | None] = mapped_column(Integer, nullable=True)           # 1-5
    completion_pain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Engine decision flags (for telemetry / future analysis)
    red_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    fatigue_reduction: Mapped[bool] = mapped_column(Boolean, default=False)

    # Reminder tracking
    morning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    evening_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    checkin_done: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="session_logs")
    workout: Mapped["Workout | None"] = relationship()


class WhitelistEntry(Base):
    __tablename__ = "whitelist"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    added_by: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
