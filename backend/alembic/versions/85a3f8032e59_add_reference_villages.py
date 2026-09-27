"""add reference villages

Revision ID: 85a3f8032e59
Revises: 3b1447d1b6cc
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# ============================================================
# Migration metadata
# ============================================================

revision: str = "85a3f8032e59"
down_revision: Union[str, None] = "3b1447d1b6cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# Upgrade
# ============================================================

def upgrade() -> None:

    # --------------------------------------------------------
    # 1. Create reference schema
    # --------------------------------------------------------

    op.execute(
        "CREATE SCHEMA IF NOT EXISTS reference"
    )

    # --------------------------------------------------------
    # 2. Create reference villages table
    # --------------------------------------------------------

    op.create_table(
        "villages",

        # ----------------------------------------------------
        # Primary key
        # ----------------------------------------------------

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        # ----------------------------------------------------
        # District
        # ----------------------------------------------------

        sa.Column(
            "district_code",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "district_name",
            sa.String(255),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Taluka
        # ----------------------------------------------------

        sa.Column(
            "taluka_code",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "taluka_name",
            sa.String(255),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Village
        # ----------------------------------------------------

        sa.Column(
            "village_code",
            sa.String(100),
            nullable=True,
        ),

        sa.Column(
            "village_name",
            sa.String(255),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Local / regional name
        # ----------------------------------------------------

        sa.Column(
            "local_name",
            sa.String(255),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Local-body type
        # ----------------------------------------------------

        sa.Column(
            "lb_type",
            sa.String(20),
            nullable=True,
        ),

        # ----------------------------------------------------
        # eFerfar code
        # ----------------------------------------------------

        sa.Column(
            "eferfar_code",
            sa.String(100),
            nullable=True,
        ),

        # ----------------------------------------------------
        # LGD discrete code
        # ----------------------------------------------------

        sa.Column(
            "lgd_discrete_code",
            sa.String(100),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Timestamp
        # ----------------------------------------------------

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Primary key
        # ----------------------------------------------------

        sa.PrimaryKeyConstraint(
            "id"
        ),

        schema="reference",
    )

    # --------------------------------------------------------
    # 3. Indexes
    # --------------------------------------------------------

    op.create_index(
        "ix_reference_villages_district_name",
        "villages",
        ["district_name"],
        unique=False,
        schema="reference",
    )

    op.create_index(
        "ix_reference_villages_taluka_name",
        "villages",
        ["taluka_name"],
        unique=False,
        schema="reference",
    )

    op.create_index(
        "ix_reference_villages_village_name",
        "villages",
        ["village_name"],
        unique=False,
        schema="reference",
    )

    op.create_index(
        "ix_reference_villages_eferfar_code",
        "villages",
        ["eferfar_code"],
        unique=False,
        schema="reference",
    )

    op.create_index(
        "ix_reference_villages_lgd_discrete_code",
        "villages",
        ["lgd_discrete_code"],
        unique=False,
        schema="reference",
    )


# ============================================================
# Downgrade
# ============================================================

def downgrade() -> None:

    # --------------------------------------------------------
    # 1. Drop indexes
    # --------------------------------------------------------

    op.drop_index(
        "ix_reference_villages_lgd_discrete_code",
        table_name="villages",
        schema="reference",
    )

    op.drop_index(
        "ix_reference_villages_eferfar_code",
        table_name="villages",
        schema="reference",
    )

    op.drop_index(
        "ix_reference_villages_village_name",
        table_name="villages",
        schema="reference",
    )

    op.drop_index(
        "ix_reference_villages_taluka_name",
        table_name="villages",
        schema="reference",
    )

    op.drop_index(
        "ix_reference_villages_district_name",
        table_name="villages",
        schema="reference",
    )

    # --------------------------------------------------------
    # 2. Drop table
    # --------------------------------------------------------

    op.drop_table(
        "villages",
        schema="reference",
    )

    # --------------------------------------------------------
    # 3. Drop schema
    # --------------------------------------------------------

    op.execute(
        "DROP SCHEMA IF EXISTS reference"
    )