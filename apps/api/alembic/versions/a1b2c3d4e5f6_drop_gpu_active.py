"""drop_gpu_active

Revision ID: a1b2c3d4e5f6
Revises: 2474ec93cdb5
Create Date: 2026-02-16 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "2474ec93cdb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that have created_at columns requiring microsecond precision.
_DATETIME6_COLUMNS = [
    ("users", "created_at"),
    ("auth_sessions", "created_at"),
    ("auth_sessions", "expires_at"),
    ("packs", "created_at"),
    ("sessions", "created_at"),
    ("datasets", "created_at"),
    ("competitions", "created_at"),
    ("competitions", "updated_at"),
    ("submissions", "created_at"),
    ("submission_scores", "created_at"),
]


def _is_mysql() -> bool:
    return op.get_bind().dialect.name == "mysql"


def upgrade() -> None:
    if not _is_mysql():
        return

    op.drop_constraint("uq_sessions_gpu_active", "sessions", type_="unique")
    op.drop_column("sessions", "gpu_active")

    # Upgrade DATETIME columns to microsecond precision (fsp=6).
    for table, column in _DATETIME6_COLUMNS:
        op.alter_column(table, column, type_=MySQLDATETIME(fsp=6), existing_type=sa.DateTime())


def downgrade() -> None:
    if not _is_mysql():
        return

    for table, column in reversed(_DATETIME6_COLUMNS):
        op.alter_column(table, column, type_=sa.DateTime(), existing_type=MySQLDATETIME(fsp=6))

    op.add_column("sessions", sa.Column("gpu_active", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_sessions_gpu_active", "sessions", ["gpu_id", "gpu_active"])
