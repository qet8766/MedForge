"""widen_competition_description

Revision ID: d4e5f6071829
Revises: c3d4e5f60718
Create Date: 2026-02-18 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6071829"
down_revision: str | Sequence[str] | None = "c3d4e5f60718"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("competitions", schema=None) as batch_op:
        batch_op.alter_column("description", existing_type=sa.String(4000), type_=sa.Text())


def downgrade() -> None:
    with op.batch_alter_table("competitions", schema=None) as batch_op:
        batch_op.alter_column("description", existing_type=sa.Text(), type_=sa.String(4000))
