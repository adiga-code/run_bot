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


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # workout_templates (новая таблица)
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "workout_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("day_type", sa.String(20), nullable=False),
        sa.Column("run_subtype", sa.String(30), nullable=True),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("intensity_kind", sa.String(30), nullable=True),
        sa.Column("period", sa.String(30), nullable=True),
        sa.Column("strength_format", sa.String(10), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("short_title", sa.String(100), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("micro_learning", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("media_id", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # week_plans (новая таблица)
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "week_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("period", sa.String(30), nullable=False),
        sa.Column("period_week_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("weekly_target_minutes", sa.Integer(), nullable=False),
        sa.Column("is_recovery_week", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_rollback_week", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("actual_running_minutes", sa.Integer(), nullable=True),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("keys_completed", sa.Boolean(), nullable=True),
        sa.Column("growth_eligible", sa.Boolean(), nullable=True),
        sa.Column("no_growth_reason", sa.String(100), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_week_plans_user_start", "week_plans", ["user_id", "start_date"])
    op.create_index("ix_week_plans_user_closed", "week_plans", ["user_id", "closed_at"])

    # ──────────────────────────────────────────────────────────────────────────
    # day_plans (новая таблица)
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "day_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("week_plan_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("day_type", sa.String(20), nullable=False),
        sa.Column("run_subtype", sa.String(30), nullable=True),
        sa.Column("planned_minutes", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.String(30), nullable=True),
        sa.Column("is_key", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_key_completed", sa.Boolean(), nullable=True),
        sa.Column("session_log_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["week_plan_id"], ["week_plans.id"]),
        sa.ForeignKeyConstraint(["session_log_id"], ["session_logs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_plan_id", "day_of_week", name="uq_day_plan_week_day"),
    )
    op.create_index("ix_day_plans_week_key", "day_plans", ["week_plan_id", "is_key"])

    # ──────────────────────────────────────────────────────────────────────────
    # users — новые поля
    # ──────────────────────────────────────────────────────────────────────────
    # Онбординг v2
    op.add_column("users", sa.Column("q_continuous_run_test", sa.String(10), nullable=True))
    # Доступные дни и объём
    op.add_column("users", sa.Column("available_weekdays", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("weekly_target_minutes", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("peak_volume_minutes", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("last_successful_volume", sa.Integer(), nullable=True))
    # Период и цикл
    op.add_column("users", sa.Column("current_period", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("period_start_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("period_week_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("cycle_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("cycle_start_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("program_week_number", sa.Integer(), nullable=False, server_default="1"))
    # Счётчики
    op.add_column("users", sa.Column("growth_streak", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("weeks_since_recovery", sa.Integer(), nullable=False, server_default="0"))
    # Red flag
    op.add_column("users", sa.Column("red_flag_active", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("red_flag_reason", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("red_flag_at", sa.Date(), nullable=True))
    # Точка входа
    op.add_column("users", sa.Column("has_goal_race", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("entry_point", sa.String(20), nullable=True))
    # Return-mode
    op.add_column("users", sa.Column("injury_return_active", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("target_level", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("return_mode_started_at", sa.Date(), nullable=True))
    # L3 recovery period
    op.add_column("users", sa.Column("in_macrocycle_recovery", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("macrocycle_recovery_week", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("macrocycle_peak_volume", sa.Integer(), nullable=True))
    # L1 long stage
    op.add_column("users", sa.Column("l1_long_independent", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("l1_no_pain_streak_weeks", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("l1_easy_reached_40min", sa.Boolean(), nullable=False, server_default="false"))

    # ──────────────────────────────────────────────────────────────────────────
    # session_logs — новые поля
    # ──────────────────────────────────────────────────────────────────────────
    # Связь с новой моделью
    op.add_column("session_logs", sa.Column("week_plan_id", sa.Integer(), nullable=True))
    op.add_column("session_logs", sa.Column("day_plan_id", sa.Integer(), nullable=True))
    op.add_column("session_logs", sa.Column("day_of_week", sa.Integer(), nullable=True))
    op.add_column("session_logs", sa.Column("planned_minutes", sa.Integer(), nullable=True))
    # Coach override
    op.add_column("session_logs", sa.Column("coach_override", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("session_logs", sa.Column("override_version", sa.String(20), nullable=True))
    op.add_column("session_logs", sa.Column("override_workout_template_id", sa.Integer(), nullable=True))
    op.add_column("session_logs", sa.Column("override_text", sa.Text(), nullable=True))
    op.add_column("session_logs", sa.Column("override_minutes", sa.Integer(), nullable=True))
    op.add_column("session_logs", sa.Column("approved_by_admin_id", sa.BigInteger(), nullable=True))
    op.add_column("session_logs", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    # Absence-flow
    op.add_column("session_logs", sa.Column("absence_reason", sa.String(30), nullable=True))
    op.add_column("session_logs", sa.Column("absence_reason_text", sa.Text(), nullable=True))
    op.add_column("session_logs", sa.Column("absence_responded_at", sa.DateTime(timezone=True), nullable=True))
    # Re-checkin
    op.add_column("session_logs", sa.Column("recheckin_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("session_logs", sa.Column("last_checkin_at", sa.DateTime(timezone=True), nullable=True))

    # FK constraints для session_logs (добавляем только если нужно и поддерживается СУБД)
    # Используем batch_alter_table для совместимости с SQLite
    try:
        op.create_foreign_key(
            "fk_session_logs_week_plan",
            "session_logs", "week_plans",
            ["week_plan_id"], ["id"],
        )
        op.create_foreign_key(
            "fk_session_logs_day_plan",
            "session_logs", "day_plans",
            ["day_plan_id"], ["id"],
        )
        op.create_foreign_key(
            "fk_session_logs_override_template",
            "session_logs", "workout_templates",
            ["override_workout_template_id"], ["id"],
        )
    except Exception:
        pass  # SQLite не поддерживает ADD CONSTRAINT — не критично


def downgrade() -> None:
    # ── session_logs — удалить новые поля ────────────────────────────────────
    for col in [
        "week_plan_id", "day_plan_id", "day_of_week", "planned_minutes",
        "coach_override", "override_version", "override_workout_template_id",
        "override_text", "override_minutes", "approved_by_admin_id", "approved_at",
        "absence_reason", "absence_reason_text", "absence_responded_at",
        "recheckin_count", "last_checkin_at",
    ]:
        op.drop_column("session_logs", col)

    # ── users — удалить новые поля ────────────────────────────────────────────
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

    # ── удалить таблицы ───────────────────────────────────────────────────────
    op.drop_index("ix_day_plans_week_key", "day_plans")
    op.drop_table("day_plans")
    op.drop_index("ix_week_plans_user_closed", "week_plans")
    op.drop_index("ix_week_plans_user_start", "week_plans")
    op.drop_table("week_plans")
    op.drop_table("workout_templates")
