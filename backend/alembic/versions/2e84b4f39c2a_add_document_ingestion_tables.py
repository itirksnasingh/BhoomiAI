"""add document ingestion tables

Revision ID: 2e84b4f39c2a
Revises: 351b54e0b92b
Create Date: 2026-09-11 19:57:38.093921
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2e84b4f39c2a"
down_revision: Union[str, Sequence[str], None] = "351b54e0b92b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # 1. Create the documents schema
    # ---------------------------------------------------------

    op.execute("CREATE SCHEMA IF NOT EXISTS documents")

    # ---------------------------------------------------------
    # 2. Create PostgreSQL enum types
    # ---------------------------------------------------------

    document_type_enum = postgresql.ENUM(
        "UNKNOWN",
        "SEVEN_TWELVE",
        "EIGHT_A",
        "FERFAR",
        "PROPERTY_CARD",
        "OTHER",
        name="document_type",
        schema="documents",
        create_type=False,
    )

    document_status_enum = postgresql.ENUM(
        "UPLOADED",
        "PROCESSING",
        "PROCESSED",
        "VALIDATION_REQUIRED",
        "VERIFIED",
        "FAILED",
        name="document_status",
        schema="documents",
        create_type=False,
    )

    document_type_enum.create(
        op.get_bind(),
        checkfirst=True,
    )

    document_status_enum.create(
        op.get_bind(),
        checkfirst=True,
    )

    # ---------------------------------------------------------
    # 3. Create documents table
    # ---------------------------------------------------------

    op.create_table(
        "documents",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            document_type_enum,
            nullable=False,
        ),
        sa.Column(
            "status",
            document_status_enum,
            nullable=False,
        ),
        sa.Column(
            "language",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "file_hash_sha256",
            sa.String(length=64),
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
        sa.UniqueConstraint("file_hash_sha256"),
        schema="documents",
    )

    # ---------------------------------------------------------
    # 4. Create document_files table
    # ---------------------------------------------------------

    op.create_table(
        "document_files",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        schema="documents",
    )

    op.create_index(
        op.f("ix_documents_document_files_document_id"),
        "document_files",
        ["document_id"],
        unique=False,
        schema="documents",
    )

    # ---------------------------------------------------------
    # 5. Create document_pages table
    # ---------------------------------------------------------

    op.create_table(
        "document_pages",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "page_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "image_storage_key",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="documents",
    )

    op.create_index(
        op.f("ix_documents_document_pages_document_id"),
        "document_pages",
        ["document_id"],
        unique=False,
        schema="documents",
    )


def downgrade() -> None:
    """Downgrade schema."""

    # ---------------------------------------------------------
    # 1. Remove indexes
    # ---------------------------------------------------------

    op.drop_index(
        op.f("ix_documents_document_pages_document_id"),
        table_name="document_pages",
        schema="documents",
    )

    op.drop_index(
        op.f("ix_documents_document_files_document_id"),
        table_name="document_files",
        schema="documents",
    )

    # ---------------------------------------------------------
    # 2. Remove tables
    # ---------------------------------------------------------

    op.drop_table(
        "document_pages",
        schema="documents",
    )

    op.drop_table(
        "document_files",
        schema="documents",
    )

    op.drop_table(
        "documents",
        schema="documents",
    )

    # ---------------------------------------------------------
    # 3. Remove PostgreSQL enum types
    # ---------------------------------------------------------

    document_type_enum = postgresql.ENUM(
        name="document_type",
        schema="documents",
    )

    document_status_enum = postgresql.ENUM(
        name="document_status",
        schema="documents",
    )

    document_status_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )

    document_type_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )

    # ---------------------------------------------------------
    # 4. Remove schema
    # ---------------------------------------------------------

    op.execute("DROP SCHEMA IF EXISTS documents")