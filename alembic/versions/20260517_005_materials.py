"""materials: create materials table

Revision ID: 005
Revises: 004
Create Date: 2026-05-17

"""
from typing import Sequence, Union
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id          SERIAL PRIMARY KEY,
            title       VARCHAR(300) NOT NULL,
            description TEXT,
            category    VARCHAR(20) NOT NULL DEFAULT 'free',
            price_label VARCHAR(100),
            file_id     VARCHAR(500) NOT NULL,
            file_name   VARCHAR(300),
            file_type   VARCHAR(50),
            sort_order  INTEGER NOT NULL DEFAULT 0,
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_materials_category_order "
        "ON materials(category, sort_order)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_materials_category_order")
    op.execute("DROP TABLE IF EXISTS materials")
