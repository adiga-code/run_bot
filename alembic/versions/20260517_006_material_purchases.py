"""material_purchases + price_rub on materials

Revision ID: 006
Revises: 005
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("price_rub", sa.Integer(), nullable=True))

    op.create_table(
        "material_purchases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("yookassa_id", sa.String(100), unique=True, nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mat_purchases_user", "material_purchases", ["user_id"])
    op.create_index("ix_mat_purchases_material", "material_purchases", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_mat_purchases_material", table_name="material_purchases")
    op.drop_index("ix_mat_purchases_user", table_name="material_purchases")
    op.drop_table("material_purchases")
    op.drop_column("materials", "price_rub")
