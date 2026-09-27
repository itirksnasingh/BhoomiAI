from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ReferenceVillage(Base):
    __tablename__ = "villages"

    __table_args__ = (
        Index(
            "ix_reference_villages_district_name",
            "district_name",
        ),
        Index(
            "ix_reference_villages_taluka_name",
            "taluka_name",
        ),
        Index(
            "ix_reference_villages_village_name",
            "village_name",
        ),
        Index(
            "ix_reference_villages_eferfar_code",
            "eferfar_code",
        ),
        Index(
            "ix_reference_villages_lgd_discrete_code",
            "lgd_discrete_code",
        ),
        {
            "schema": "reference",
        },
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    district_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    district_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    taluka_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    taluka_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    village_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    village_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    local_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    lb_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    eferfar_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    lgd_discrete_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )