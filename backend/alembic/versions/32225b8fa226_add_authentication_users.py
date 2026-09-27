"""add authentication users

Revision ID: 32225b8fa226
Revises: 85a3f8032e59
Create Date: 2026-09-13 11:14:37.885381

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "32225b8fa226"
down_revision: Union[str, Sequence[str], None] = "85a3f8032e59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create schema first.
    op.execute("CREATE SCHEMA auth")

    # Create PostgreSQL enum explicitly.
    op.execute(
        """
        CREATE TYPE auth.user_role AS ENUM (
            'ADMIN',
            'REVIEWER',
            'VIEWER'
        )
        """
    )

    # Reference the already-created PostgreSQL enum.
    user_role = postgresql.ENUM(
        "ADMIN",
        "REVIEWER",
        "VIEWER",
        name="user_role",
        schema="auth",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "full_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "role",
            user_role,
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="auth",
    )

    op.create_index(
        op.f("ix_auth_users_email"),
        "users",
        ["email"],
        unique=True,
        schema="auth",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_auth_users_email"),
        table_name="users",
        schema="auth",
    )

    op.drop_table(
        "users",
        schema="auth",
    )

    op.execute("DROP TYPE auth.user_role")
    op.execute("DROP SCHEMA auth")