"""add_ssh_fields

Revision ID: c3d4e5f60718
Revises: b2c3d4e5f607
Create Date: 2026-02-18 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f60718"
down_revision: str | Sequence[str] | None = "b2c3d4e5f607"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ssh_public_key", sa.String(4096), nullable=True))

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ssh_port", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("ssh_port")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("ssh_public_key")
