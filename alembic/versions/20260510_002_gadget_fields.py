"""gadget fields for user

Revision ID: 002
Revises: 001
Create Date: 2026-05-10

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("q_gadget", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("q_gadget_types", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("q_gadget_sharing", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "q_gadget_sharing")
    op.drop_column("users", "q_gadget_types")
    op.drop_column("users", "q_gadget")
