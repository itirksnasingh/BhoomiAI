"""add validation results

Revision ID: efbd486c05ed
Revises: 34f54d7ff2d7
"""

from typing import Sequence, Union

from alembic import op


revision: str = "efbd486c05ed"
down_revision: Union[str, Sequence[str], None] = "34f54d7ff2d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create validation result storage."""

    # Create schema.
    op.execute(
        "CREATE SCHEMA IF NOT EXISTS validation"
    )

    # Create enum only if it does not already exist.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n
                    ON n.oid = t.typnamespace
                WHERE t.typname = 'validation_status'
                  AND n.nspname = 'validation'
            ) THEN
                CREATE TYPE validation.validation_status
                AS ENUM (
                    'PASS',
                    'WARNING',
                    'REVIEW'
                );
            END IF;
        END
        $$;
        """
    )

    # Create table using the already-existing enum.
    op.execute(
        """
        CREATE TABLE validation.validation_results (
            id UUID NOT NULL,
            extracted_field_id UUID NOT NULL,
            rule_name VARCHAR(100) NOT NULL,
            status validation.validation_status NOT NULL,
            message TEXT NOT NULL,
            confidence DOUBLE PRECISION,
            created_at TIMESTAMPTZ NOT NULL,

            CONSTRAINT validation_results_pkey
                PRIMARY KEY (id),

            CONSTRAINT validation_results_extracted_field_id_fkey
                FOREIGN KEY (extracted_field_id)
                REFERENCES extraction.extracted_fields(id)
                ON DELETE CASCADE
        )
        """
    )

    # Index for field-level validation lookups.
    op.execute(
        """
        CREATE INDEX
        ix_validation_validation_results_extracted_field_id
        ON validation.validation_results
        (extracted_field_id)
        """
    )


def downgrade() -> None:
    """Remove validation result storage."""

    op.execute(
        """
        DROP INDEX IF EXISTS
        validation.ix_validation_validation_results_extracted_field_id
        """
    )

    op.execute(
        """
        DROP TABLE IF EXISTS
        validation.validation_results
        """
    )

    op.execute(
        """
        DROP TYPE IF EXISTS
        validation.validation_status
        """
    )

    op.execute(
        "DROP SCHEMA IF EXISTS validation"
    )