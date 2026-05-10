"""v2 migration: new fields + WeekPlan, DayPlan, WorkoutTemplate tables

Revision ID: 001
Revises:
Create Date: 2026-05-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_not_exists(table: str, column: str, ddl: str) -> None:
    op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}")


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # workout_templates (новая таблица)
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS workout_templates (
            id SERIAL NOT NULL,
            level INTEGER NOT NULL,
            day_type VARCHAR(20) NOT NULL,
            run_subtype VARCHAR(30),
            version VARCHAR(20) NOT NULL,
            intensity_kind VARCHAR(30),
            period VARCHAR(30),
            strength_format VARCHAR(10),
            title VARCHAR(200) NOT NULL,
            short_title VARCHAR(100),
            text TEXT NOT NULL,
            micro_learning TEXT,
            video_url VARCHAR(500),
            media_id VARCHAR(200),
            PRIMARY KEY (id)
        )
    """)

    # ──────────────────────────────────────────────────────────────────────────
    # week_plans (новая таблица)
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS week_plans (
            id SERIAL NOT NULL,
            user_id BIGINT NOT NULL,
            week_number INTEGER NOT NULL,
            cycle_number INTEGER NOT NULL DEFAULT 1,
            period VARCHAR(30) NOT NULL,
            period_week_number INTEGER NOT NULL DEFAULT 1,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            weekly_target_minutes INTEGER NOT NULL,
            is_recovery_week BOOLEAN NOT NULL DEFAULT false,
            is_rollback_week BOOLEAN NOT NULL DEFAULT false,
            actual_running_minutes INTEGER,
            completion_rate FLOAT,
            keys_completed BOOLEAN,
            growth_eligible BOOLEAN,
            no_growth_reason VARCHAR(100),
            closed_at TIMESTAMPTZ,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_week_plans_user_start ON week_plans (user_id, start_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_week_plans_user_closed ON week_plans (user_id, closed_at)")

    # ──────────────────────────────────────────────────────────────────────────
    # day_plans (новая таблица)
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS day_plans (
            id SERIAL NOT NULL,
            week_plan_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            day_type VARCHAR(20) NOT NULL,
            run_subtype VARCHAR(30),
            planned_minutes INTEGER NOT NULL,
            intensity VARCHAR(30),
            is_key BOOLEAN NOT NULL DEFAULT false,
            is_key_completed BOOLEAN,
            session_log_id INTEGER,
            PRIMARY KEY (id),
            FOREIGN KEY (week_plan_id) REFERENCES week_plans(id),
            FOREIGN KEY (session_log_id) REFERENCES session_logs(id),
            UNIQUE (week_plan_id, day_of_week)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_day_plans_week_key ON day_plans (week_plan_id, is_key)")

    # ──────────────────────────────────────────────────────────────────────────
    # users — новые поля
    # ──────────────────────────────────────────────────────────────────────────
    _add_column_if_not_exists("users", "q_continuous_run_test", "VARCHAR(10)")
    _add_column_if_not_exists("users", "available_weekdays", "VARCHAR(20)")
    _add_column_if_not_exists("users", "weekly_target_minutes", "INTEGER")
    _add_column_if_not_exists("users", "peak_volume_minutes", "INTEGER")
    _add_column_if_not_exists("users", "last_successful_volume", "INTEGER")
    _add_column_if_not_exists("users", "current_period", "VARCHAR(30)")
    _add_column_if_not_exists("users", "period_start_date", "DATE")
    _add_column_if_not_exists("users", "period_week_number", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_not_exists("users", "cycle_number", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_not_exists("users", "cycle_start_date", "DATE")
    _add_column_if_not_exists("users", "program_week_number", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_not_exists("users", "growth_streak", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_not_exists("users", "weeks_since_recovery", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_not_exists("users", "red_flag_active", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_not_exists("users", "red_flag_reason", "VARCHAR(100)")
    _add_column_if_not_exists("users", "red_flag_at", "DATE")
    _add_column_if_not_exists("users", "has_goal_race", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_not_exists("users", "entry_point", "VARCHAR(20)")
    _add_column_if_not_exists("users", "injury_return_active", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_not_exists("users", "target_level", "INTEGER")
    _add_column_if_not_exists("users", "return_mode_started_at", "DATE")
    _add_column_if_not_exists("users", "in_macrocycle_recovery", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_not_exists("users", "macrocycle_recovery_week", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_not_exists("users", "macrocycle_peak_volume", "INTEGER")
    _add_column_if_not_exists("users", "l1_long_independent", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_not_exists("users", "l1_no_pain_streak_weeks", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_not_exists("users", "l1_easy_reached_40min", "BOOLEAN NOT NULL DEFAULT false")

    # ──────────────────────────────────────────────────────────────────────────
    # session_logs — новые поля
    # ──────────────────────────────────────────────────────────────────────────
    _add_column_if_not_exists("session_logs", "week_plan_id", "INTEGER")
    _add_column_if_not_exists("session_logs", "day_plan_id", "INTEGER")
    _add_column_if_not_exists("session_logs", "day_of_week", "INTEGER")
    _add_column_if_not_exists("session_logs", "planned_minutes", "INTEGER")
    _add_column_if_not_exists("session_logs", "coach_override", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_not_exists("session_logs", "override_version", "VARCHAR(20)")
    _add_column_if_not_exists("session_logs", "override_workout_template_id", "INTEGER")
    _add_column_if_not_exists("session_logs", "override_text", "TEXT")
    _add_column_if_not_exists("session_logs", "override_minutes", "INTEGER")
    _add_column_if_not_exists("session_logs", "approved_by_admin_id", "BIGINT")
    _add_column_if_not_exists("session_logs", "approved_at", "TIMESTAMPTZ")
    _add_column_if_not_exists("session_logs", "absence_reason", "VARCHAR(30)")
    _add_column_if_not_exists("session_logs", "absence_reason_text", "TEXT")
    _add_column_if_not_exists("session_logs", "absence_responded_at", "TIMESTAMPTZ")
    _add_column_if_not_exists("session_logs", "recheckin_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_not_exists("session_logs", "last_checkin_at", "TIMESTAMPTZ")

    # FK constraints — пропускаем если уже существуют
    try:
        op.create_foreign_key(
            "fk_session_logs_week_plan", "session_logs", "week_plans", ["week_plan_id"], ["id"],
        )
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "fk_session_logs_day_plan", "session_logs", "day_plans", ["day_plan_id"], ["id"],
        )
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "fk_session_logs_override_template", "session_logs", "workout_templates",
            ["override_workout_template_id"], ["id"],
        )
    except Exception:
        pass


def downgrade() -> None:
    for col in [
        "week_plan_id", "day_plan_id", "day_of_week", "planned_minutes",
        "coach_override", "override_version", "override_workout_template_id",
        "override_text", "override_minutes", "approved_by_admin_id", "approved_at",
        "absence_reason", "absence_reason_text", "absence_responded_at",
        "recheckin_count", "last_checkin_at",
    ]:
        op.drop_column("session_logs", col)

    for col in [
        "q_continuous_run_test", "available_weekdays", "weekly_target_minutes",
        "peak_volume_minutes", "last_successful_volume", "current_period",
        "period_start_date", "period_week_number", "cycle_number", "cycle_start_date",
        "program_week_number", "growth_streak", "weeks_since_recovery",
        "red_flag_active", "red_flag_reason", "red_flag_at", "has_goal_race",
        "entry_point", "injury_return_active", "target_level", "return_mode_started_at",
        "in_macrocycle_recovery", "macrocycle_recovery_week", "macrocycle_peak_volume",
        "l1_long_independent", "l1_no_pain_streak_weeks", "l1_easy_reached_40min",
    ]:
        op.drop_column("users", col)

    op.drop_index("ix_day_plans_week_key", "day_plans")
    op.drop_table("day_plans")
    op.drop_index("ix_week_plans_user_closed", "week_plans")
    op.drop_index("ix_week_plans_user_start", "week_plans")
    op.drop_table("week_plans")
    op.drop_table("workout_templates")
