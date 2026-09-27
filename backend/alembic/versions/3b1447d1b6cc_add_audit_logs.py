"""add audit logs

Revision ID: 3b1447d1b6cc
Revises: bae7c5189f0f
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# ============================================================
# Migration metadata
# ============================================================

revision: str = "3b1447d1b6cc"
down_revision: Union[str, None] = "bae7c5189f0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# Upgrade
# ============================================================

def upgrade() -> None:

    # --------------------------------------------------------
    # 1. Create audit schema
    # --------------------------------------------------------

    op.execute(
        "CREATE SCHEMA IF NOT EXISTS audit"
    )

    # --------------------------------------------------------
    # 2. Create audit action enum
    #
    # The enum is created manually so this migration is
    # deterministic and safe if the type already exists.
    # --------------------------------------------------------

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'audit_action'
                AND typnamespace = (
                    SELECT oid
                    FROM pg_namespace
                    WHERE nspname = 'audit'
                )
            ) THEN
                CREATE TYPE audit.audit_action AS ENUM (
                    'ACCEPT',
                    'EDIT',
                    'REJECT',
                    'VERIFY',
                    'FLAG'
                );
            END IF;
        END
        $$;
        """
    )

    # --------------------------------------------------------
    # 3. Create audit_logs table
    # --------------------------------------------------------

    op.create_table(
        "audit_logs",

        # ----------------------------------------------------
        # Primary key
        # ----------------------------------------------------

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Document being audited
        # ----------------------------------------------------

        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Specific extracted field being reviewed
        # ----------------------------------------------------

        sa.Column(
            "extracted_field_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Human action
        #
        # IMPORTANT:
        # create_type=False prevents SQLAlchemy from trying
        # to create audit.audit_action again.
        # ----------------------------------------------------

        sa.Column(
            "action",
            postgresql.ENUM(
                "ACCEPT",
                "EDIT",
                "REJECT",
                "VERIFY",
                "FLAG",
                name="audit_action",
                schema="audit",
                create_type=False,
            ),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Previous AI/extracted value
        # ----------------------------------------------------

        sa.Column(
            "old_value",
            sa.Text(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # New human-reviewed value
        # ----------------------------------------------------

        sa.Column(
            "new_value",
            sa.Text(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Review decision
        # ----------------------------------------------------

        sa.Column(
            "decision",
            sa.String(length=50),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Human explanation
        # ----------------------------------------------------

        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Reviewer identifier
        #
        # Nullable for now because authentication/RBAC is
        # not yet wired into the MVP.
        # ----------------------------------------------------

        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),

        # ----------------------------------------------------
        # Audit timestamp
        # ----------------------------------------------------

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Foreign keys
        # ----------------------------------------------------

        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.documents.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["extracted_field_id"],
            ["extraction.extracted_fields.id"],
            ondelete="SET NULL",
        ),

        # ----------------------------------------------------
        # Primary key
        # ----------------------------------------------------

        sa.PrimaryKeyConstraint(
            "id"
        ),

        schema="audit",
    )

    # --------------------------------------------------------
    # 4. Indexes
    # --------------------------------------------------------

    op.create_index(
        "ix_audit_logs_document_id",
        "audit_logs",
        ["document_id"],
        unique=False,
        schema="audit",
    )

    op.create_index(
        "ix_audit_logs_extracted_field_id",
        "audit_logs",
        ["extracted_field_id"],
        unique=False,
        schema="audit",
    )

    op.create_index(
        "ix_audit_logs_reviewer_id",
        "audit_logs",
        ["reviewer_id"],
        unique=False,
        schema="audit",
    )


# ============================================================
# Downgrade
# ============================================================

def downgrade() -> None:

    # --------------------------------------------------------
    # 1. Drop indexes
    # --------------------------------------------------------

    op.drop_index(
        "ix_audit_logs_reviewer_id",
        table_name="audit_logs",
        schema="audit",
    )

    op.drop_index(
        "ix_audit_logs_extracted_field_id",
        table_name="audit_logs",
        schema="audit",
    )

    op.drop_index(
        "ix_audit_logs_document_id",
        table_name="audit_logs",
        schema="audit",
    )

    # --------------------------------------------------------
    # 2. Drop audit table
    # --------------------------------------------------------

    op.drop_table(
        "audit_logs",
        schema="audit",
    )

    # --------------------------------------------------------
    # 3. Drop enum
    # --------------------------------------------------------

    op.execute(
        """
        DROP TYPE IF EXISTS audit.audit_action
        """
    )

    # --------------------------------------------------------
    # 4. Drop audit schema
    # --------------------------------------------------------

    op.execute(
        """
        DROP SCHEMA IF EXISTS audit
        """
    )