import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.reference import ReferenceVillage


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip().casefold()

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)

    # Remove common punctuation
    value = re.sub(r"[.,;:()\[\]{}]", "", value)

    return value


class ReferenceMatcher:
    """Matches extracted land-record fields against reference data."""

    def __init__(self, db: Session):
        self.db = db

    def match_village(
        self,
        village_name: str,
        taluka_name: str | None = None,
        district_name: str | None = None,
    ) -> dict:
        normalized_village = normalize_text(village_name)

        if not normalized_village:
            return {
                "status": "NOT_FOUND",
                "message": "Village value is empty.",
                "matched_record": None,
            }

        # Fetch candidate village records.
        query = select(ReferenceVillage).where(
            or_(
                ReferenceVillage.village_name.is_not(None),
                ReferenceVillage.local_name.is_not(None),
            )
        )

        candidates = self.db.execute(query).scalars().all()

        # First: exact village-name match.
        village_matches = []

        for record in candidates:
            names = {
                normalize_text(record.village_name),
                normalize_text(record.local_name),
            }

            if normalized_village in names:
                village_matches.append(record)

        # Narrow by taluka when available.
        if taluka_name and village_matches:
            normalized_taluka = normalize_text(taluka_name)

            narrowed = [
                record
                for record in village_matches
                if normalize_text(record.taluka_name) == normalized_taluka
            ]

            if narrowed:
                village_matches = narrowed

        # Narrow by district when available.
        if district_name and village_matches:
            normalized_district = normalize_text(district_name)

            narrowed = [
                record
                for record in village_matches
                if normalize_text(record.district_name) == normalized_district
            ]

            if narrowed:
                village_matches = narrowed

        if not village_matches:
            return {
                "status": "NOT_FOUND",
                "message": (
                    f"Village '{village_name}' was not found in the "
                    "available reference dataset."
                ),
                "matched_record": None,
            }

        if len(village_matches) > 1:
            return {
                "status": "AMBIGUOUS",
                "message": (
                    f"Village '{village_name}' matched multiple reference "
                    "records. Additional location context is required."
                ),
                "matched_record": None,
            }

        record = village_matches[0]

        return {
            "status": "MATCHED",
            "message": (
                f"Village '{village_name}' matched the reference dataset."
            ),
            "matched_record": record,
        }