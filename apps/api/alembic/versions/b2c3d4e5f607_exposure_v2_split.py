"""exposure_v2_split

Revision ID: b2c3d4e5f607
Revises: a1b2c3d4e5f6
Create Date: 2026-02-17 20:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f607"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PACK_EXPOSURE = sa.Enum("EXTERNAL", "INTERNAL", "BOTH", name="pack_exposure")
_SESSION_EXPOSURE = sa.Enum("EXTERNAL", "INTERNAL", name="exposure")
_COMPETITION_EXPOSURE = sa.Enum("EXTERNAL", "INTERNAL", name="competition_exposure")
_DATASET_EXPOSURE = sa.Enum("EXTERNAL", "INTERNAL", name="dataset_exposure")

_PACK_TIER = sa.Enum("PUBLIC", "PRIVATE", "BOTH", name="pack_tier")
_TIER = sa.Enum("PUBLIC", "PRIVATE", name="tier")
_COMPETITION_TIER = sa.Enum("PUBLIC", "PRIVATE", name="competition_tier")


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("can_use_internal", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("packs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "exposure",
                _PACK_EXPOSURE,
                nullable=False,
                server_default="EXTERNAL",
            )
        )

    op.execute(
        """
        UPDATE packs
        SET exposure = CASE tier
            WHEN 'PUBLIC' THEN 'EXTERNAL'
            WHEN 'PRIVATE' THEN 'INTERNAL'
            ELSE 'BOTH'
        END
        """
    )

    with op.batch_alter_table("packs", schema=None) as batch_op:
        batch_op.drop_column("tier")

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "exposure",
                _SESSION_EXPOSURE,
                nullable=False,
                server_default="EXTERNAL",
            )
        )

    op.execute(
        """
        UPDATE sessions
        SET exposure = CASE tier
            WHEN 'PUBLIC' THEN 'EXTERNAL'
            WHEN 'PRIVATE' THEN 'INTERNAL'
            ELSE 'EXTERNAL'
        END
        """
    )

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("tier")

    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "exposure",
                _DATASET_EXPOSURE,
                nullable=False,
                server_default="EXTERNAL",
            )
        )

    with op.batch_alter_table("competitions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "competition_exposure",
                _COMPETITION_EXPOSURE,
                nullable=False,
                server_default="EXTERNAL",
            )
        )

    op.execute(
        """
        UPDATE competitions
        SET competition_exposure = CASE competition_tier
            WHEN 'PUBLIC' THEN 'EXTERNAL'
            WHEN 'PRIVATE' THEN 'INTERNAL'
            ELSE 'EXTERNAL'
        END
        """
    )

    with op.batch_alter_table("competitions", schema=None) as batch_op:
        batch_op.drop_column("competition_tier")


def downgrade() -> None:
    with op.batch_alter_table("competitions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "competition_tier",
                _COMPETITION_TIER,
                nullable=False,
                server_default="PUBLIC",
            )
        )

    op.execute(
        """
        UPDATE competitions
        SET competition_tier = CASE competition_exposure
            WHEN 'EXTERNAL' THEN 'PUBLIC'
            WHEN 'INTERNAL' THEN 'PRIVATE'
            ELSE 'PUBLIC'
        END
        """
    )

    with op.batch_alter_table("competitions", schema=None) as batch_op:
        batch_op.drop_column("competition_exposure")

    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.drop_column("exposure")

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tier",
                _TIER,
                nullable=False,
                server_default="PUBLIC",
            )
        )

    op.execute(
        """
        UPDATE sessions
        SET tier = CASE exposure
            WHEN 'EXTERNAL' THEN 'PUBLIC'
            WHEN 'INTERNAL' THEN 'PRIVATE'
            ELSE 'PUBLIC'
        END
        """
    )

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("exposure")

    with op.batch_alter_table("packs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tier",
                _PACK_TIER,
                nullable=False,
                server_default="PUBLIC",
            )
        )

    op.execute(
        """
        UPDATE packs
        SET tier = CASE exposure
            WHEN 'EXTERNAL' THEN 'PUBLIC'
            WHEN 'INTERNAL' THEN 'PRIVATE'
            ELSE 'BOTH'
        END
        """
    )

    with op.batch_alter_table("packs", schema=None) as batch_op:
        batch_op.drop_column("exposure")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("can_use_internal")
