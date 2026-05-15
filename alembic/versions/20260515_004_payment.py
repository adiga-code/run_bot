"""payment: add trial/access fields to users, create payments table

Revision ID: 004
Revises: 003
Create Date: 2026-05-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ
    """)
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS access_until DATE
    """)
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS subscription_type VARCHAR(20) NOT NULL DEFAULT 'trial'
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(telegram_id),
            yookassa_id VARCHAR(100) UNIQUE,
            amount INTEGER NOT NULL,
            plan_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            payment_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            confirmed_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments")
    op.drop_column("users", "subscription_type")
    op.drop_column("users", "access_until")
    op.drop_column("users", "trial_started_at")
