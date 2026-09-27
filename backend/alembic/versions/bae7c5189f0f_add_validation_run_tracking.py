"""add validation run tracking

Revision ID: bae7c5189f0f
Revises: 042fbe17e758
Create Date: 2026-09-12 01:24:17.770910

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bae7c5189f0f"
down_revision: Union[str, Sequence[str], None] = "042fbe17e758"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # =========================================================
    # 1. Create validation run status enum if it does not exist
    # =========================================================

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_namespace n
                        ON n.oid = t.typnamespace
                    WHERE t.typname = 'validation_run_status'
                      AND n.nspname = 'validation'
                ) THEN
                    CREATE TYPE validation.validation_run_status
                    AS ENUM (
                        'PENDING',
                        'RUNNING',
                        'COMPLETED',
                        'FAILED'
                    );
                END IF;
            END
            $$;
            """
        )
    )

    # =========================================================
    # 2. Create validation_runs table
    # =========================================================

    op.execute(
        sa.text(
            """
            CREATE TABLE validation.validation_runs (
                id UUID NOT NULL,
                document_id UUID NOT NULL,
                extraction_run_id UUID NULL,
                engine VARCHAR(100) NOT NULL,
                engine_version VARCHAR(100) NULL,
                status validation.validation_run_status NOT NULL,
                confidence DOUBLE PRECISION NULL,
                error_message TEXT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                completed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL,

                CONSTRAINT validation_runs_pkey
                    PRIMARY KEY (id),

                CONSTRAINT validation_runs_document_id_fkey
                    FOREIGN KEY (document_id)
                    REFERENCES documents.documents (id)
                    ON DELETE CASCADE,

                CONSTRAINT validation_runs_extraction_run_id_fkey
                    FOREIGN KEY (extraction_run_id)
                    REFERENCES extraction.extraction_runs (id)
                    ON DELETE SET NULL
            );
            """
        )
    )

    # =========================================================
    # 3. Create indexes for validation_runs
    # =========================================================

    op.create_index(
        "ix_validation_validation_runs_document_id",
        "validation_runs",
        ["document_id"],
        unique=False,
        schema="validation",
    )

    op.create_index(
        "ix_validation_validation_runs_extraction_run_id",
        "validation_runs",
        ["extraction_run_id"],
        unique=False,
        schema="validation",
    )

    # =========================================================
    # 4. Add validation_run_id temporarily as nullable
    # =========================================================

    op.add_column(
        "validation_results",
        sa.Column(
            "validation_run_id",
            sa.UUID(),
            nullable=True,
        ),
        schema="validation",
    )

    # =========================================================
    # 5. Create legacy validation runs
    # =========================================================
    #
    # One historical run is created for every document that
    # already has validation results.
    #
    # =========================================================

    op.execute(
        sa.text(
            """
            INSERT INTO validation.validation_runs (
                id,
                document_id,
                extraction_run_id,
                engine,
                engine_version,
                status,
                confidence,
                error_message,
                started_at,
                completed_at,
                created_at
            )
            SELECT
                gen_random_uuid(),
                dp.document_id,
                NULL,
                'legacy',
                'pre-run-tracking',
                'COMPLETED'::validation.validation_run_status,
                NULL,
                'Historical validation results migrated before validation run tracking was introduced.',
                MIN(vr.created_at),
                MAX(vr.created_at),
                MIN(vr.created_at)
            FROM validation.validation_results AS vr
            JOIN extraction.extracted_fields AS ef
                ON ef.id = vr.extracted_field_id
            JOIN documents.document_pages AS dp
                ON dp.id = ef.document_page_id
            GROUP BY dp.document_id;
            """
        )
    )

    # =========================================================
    # 6. Link existing validation results to legacy runs
    # =========================================================
    #
    # IMPORTANT:
    # Use a subquery so PostgreSQL does not have to reference
    # the UPDATE target alias from inside a JOIN condition.
    #
    # =========================================================

    op.execute(
        sa.text(
            """
            UPDATE validation.validation_results AS vr
            SET validation_run_id = legacy.id
            FROM (
                SELECT
                    ef.id AS extracted_field_id,
                    dp.document_id
                FROM extraction.extracted_fields AS ef
                JOIN documents.document_pages AS dp
                    ON dp.id = ef.document_page_id
            ) AS field_documents
            JOIN validation.validation_runs AS legacy
                ON legacy.document_id = field_documents.document_id
            WHERE vr.extracted_field_id = field_documents.extracted_field_id
              AND legacy.engine = 'legacy'
              AND legacy.engine_version = 'pre-run-tracking';
            """
        )
    )

    # =========================================================
    # 7. Make validation_run_id NOT NULL
    # =========================================================

    op.alter_column(
        "validation_results",
        "validation_run_id",
        existing_type=sa.UUID(),
        nullable=False,
        schema="validation",
    )

    # =========================================================
    # 8. Add index
    # =========================================================

    op.create_index(
        "ix_validation_validation_results_validation_run_id",
        "validation_results",
        ["validation_run_id"],
        unique=False,
        schema="validation",
    )

    # =========================================================
    # 9. Add foreign key
    # =========================================================

    op.create_foreign_key(
        "fk_validation_results_validation_run_id",
        "validation_results",
        "validation_runs",
        ["validation_run_id"],
        ["id"],
        source_schema="validation",
        referent_schema="validation",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""

    # =========================================================
    # 1. Remove foreign key
    # =========================================================

    op.drop_constraint(
        "fk_validation_results_validation_run_id",
        "validation_results",
        schema="validation",
        type_="foreignkey",
    )

    # =========================================================
    # 2. Remove index
    # =========================================================

    op.drop_index(
        "ix_validation_validation_results_validation_run_id",
        table_name="validation_results",
        schema="validation",
    )

    # =========================================================
    # 3. Remove validation_run_id
    # =========================================================

    op.drop_column(
        "validation_results",
        "validation_run_id",
        schema="validation",
    )

    # =========================================================
    # 4. Remove validation_runs indexes
    # =========================================================

    op.drop_index(
        "ix_validation_validation_runs_extraction_run_id",
        table_name="validation_runs",
        schema="validation",
    )

    op.drop_index(
        "ix_validation_validation_runs_document_id",
        table_name="validation_runs",
        schema="validation",
    )

    # =========================================================
    # 5. Remove validation_runs table
    # =========================================================

    op.drop_table(
        "validation_runs",
        schema="validation",
    )

    # =========================================================
    # 6. Remove enum
    # =========================================================

    op.execute(
        sa.text(
            """
            DROP TYPE IF EXISTS validation.validation_run_status;
            """
        )
    )