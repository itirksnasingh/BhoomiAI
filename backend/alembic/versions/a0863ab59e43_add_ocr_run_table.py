"""add OCR run table

Revision ID: a0863ab59e43
Revises: 2e84b4f39c2a
Create Date: 2026-09-11 20:19:23.265844
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a0863ab59e43"
down_revision: Union[str, Sequence[str], None] = "2e84b4f39c2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create application schema.
    op.execute("CREATE SCHEMA IF NOT EXISTS extraction")

    # Create PostgreSQL enum explicitly.
    ocr_run_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        name="ocr_run_status",
        schema="extraction",
        create_type=False,
    )

    ocr_run_status_enum.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "ocr_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_page_id", sa.UUID(), nullable=False),
        sa.Column("engine", sa.String(length=100), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            ocr_run_status_enum,
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_page_id"],
            ["documents.document_pages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="extraction",
    )

    op.create_index(
        op.f("ix_extraction_ocr_runs_document_page_id"),
        "ocr_runs",
        ["document_page_id"],
        unique=False,
        schema="extraction",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_extraction_ocr_runs_document_page_id"),
        table_name="ocr_runs",
        schema="extraction",
    )

    op.drop_table(
        "ocr_runs",
        schema="extraction",
    )

    ocr_run_status_enum = postgresql.ENUM(
        name="ocr_run_status",
        schema="extraction",
    )

    ocr_run_status_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )

    op.execute("DROP SCHEMA IF EXISTS extraction")