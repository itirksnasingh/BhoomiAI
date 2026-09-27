"""initial database structure

Revision ID: 351b54e0b92b
Revises:
Create Date: 2026-09-11 19:37:10.941813
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "351b54e0b92b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create the application system schema first.
    op.execute("CREATE SCHEMA IF NOT EXISTS system")

    # Create schema information table.
    op.create_table(
        "schema_info",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="system",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table(
        "schema_info",
        schema="system",
    )