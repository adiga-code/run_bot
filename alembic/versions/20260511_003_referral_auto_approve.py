"""referral_links: add is_active and auto_approve columns

Revision ID: 003
Revises: 002
Create Date: 2026-05-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # is_active was added to the model without a migration — add it idempotently
    op.execute("""
        ALTER TABLE referral_links
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true
    """)
    op.execute("""
        ALTER TABLE referral_links
        ADD COLUMN IF NOT EXISTS auto_approve BOOLEAN NOT NULL DEFAULT false
    """)


def downgrade() -> None:
    op.drop_column("referral_links", "auto_approve")
    op.drop_column("referral_links", "is_active")
