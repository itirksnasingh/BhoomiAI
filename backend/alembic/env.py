from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import get_settings
from app.db.session import Base

# -------------------------------------------------------------------
# Import ALL application models
# -------------------------------------------------------------------
# These imports are intentionally explicit so SQLAlchemy/Alembic
# registers every model in Base.metadata before autogeneration.
from app.models.system import SchemaInfo

from app.models.documents import (
    Document,
    DocumentFile,
    DocumentPage,
)

from app.models.extraction import (
    OCRRun,
    OCRBlock,
    ExtractedField,
    FieldEvidence,
    ExtractionRun,
)

from app.models.validation import (
    ValidationResult,
    ValidationRun,
)


# -------------------------------------------------------------------
# Alembic Config object
# -------------------------------------------------------------------
config = context.config


# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# -------------------------------------------------------------------
# SQLAlchemy metadata
# -------------------------------------------------------------------
target_metadata = Base.metadata


# -------------------------------------------------------------------
# Database object filtering
# -------------------------------------------------------------------
def include_name(name, type_, parent_names):
    """
    Control which database objects Alembic considers during
    autogeneration.

    PostGIS creates spatial_ref_sys automatically. It is not an
    application-managed table, so Alembic must ignore it.
    """

    if type_ == "table" and name == "spatial_ref_sys":
        return False

    return True


# -------------------------------------------------------------------
# Database URL
# -------------------------------------------------------------------
def get_database_url() -> str:
    return get_settings().database_url


# -------------------------------------------------------------------
# Offline migrations
# -------------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in offline mode.

    This generates SQL without establishing a live database
    connection.
    """

    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------------------------
# Online migrations
# -------------------------------------------------------------------
def run_migrations_online() -> None:
    """
    Run migrations against the live PostgreSQL database.
    """

    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------------------------
# Migration entry point
# -------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()