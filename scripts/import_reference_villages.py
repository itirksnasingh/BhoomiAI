import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.reference import ReferenceVillage


DEFAULT_JSON_PATH = (
    BACKEND_DIR.parent
    / "data"
    / "reference"
    / "maharashtra_villages.json"
)

BATCH_SIZE = 1000


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def load_records(json_path: Path):
    print("Reading reference file:")
    print(f"  {json_path}")

    if not json_path.exists():
        raise FileNotFoundError(
            f"Reference JSON not found: {json_path}"
        )

    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "Expected the JSON root to be an object."
        )

    if payload.get("status") != "success":
        raise ValueError(
            f"Reference JSON status is not success: "
            f"{payload.get('status')}"
        )

    records = payload.get("data")

    if not isinstance(records, list):
        raise ValueError(
            "Expected JSON field 'data' to contain a list."
        )

    print(f"Records found: {len(records):,}")

    return records


def convert_record(record: dict) -> dict:
    return {
        "district_code": clean(
            record.get("eferfar_dist_code")
        ),
        "district_name": clean(
            record.get("district_name")
        ),
        "taluka_code": clean(
            record.get("eferfar_taluka_code")
        ),
        "taluka_name": clean(
            record.get("taluka_name")
        ),
        "village_code": clean(
            record.get("eferfar_village_code")
        ),
        "village_name": clean(
            record.get("village_name")
        ),
        "local_name": clean(
            record.get("eferfar_local_name")
        ),
        "lb_type": clean(
            record.get("eferfar_lbtype")
        ),
        "eferfar_code": clean(
            record.get("eferfar_code")
        ),
        "lgd_discrete_code": clean(
            record.get("lgd_discrete_code")
        ),
    }


def import_records(records, replace=False):
    db: Session = SessionLocal()

    try:
        existing_count = db.query(
            ReferenceVillage
        ).count()

        print(
            f"Existing reference records: "
            f"{existing_count:,}"
        )

        if existing_count > 0 and not replace:
            raise RuntimeError(
                "reference.villages already contains data. "
                "Use --replace if you intentionally want "
                "to replace it."
            )

        if replace and existing_count > 0:
            print("Removing existing reference records...")

            db.execute(delete(ReferenceVillage))
            db.commit()

            print("Existing reference records removed.")

        total = len(records)

        for start in range(0, total, BATCH_SIZE):

            batch_records = records[
                start:start + BATCH_SIZE
            ]

            objects = [
                ReferenceVillage(
                    **convert_record(record)
                )
                for record in batch_records
            ]

            db.add_all(objects)
            db.commit()

            imported = min(
                start + len(batch_records),
                total
            )

            print(
                f"Imported {imported:,}/{total:,} "
                f"({imported / total * 100:.1f}%)"
            )

        final_count = db.query(
            ReferenceVillage
        ).count()

        print()
        print("=" * 60)
        print("REFERENCE IMPORT COMPLETE")
        print("=" * 60)

        print(f"Source records : {total:,}")
        print(f"DB records     : {final_count:,}")

        if final_count != total:
            raise RuntimeError(
                f"Record count mismatch: "
                f"expected {total:,}, "
                f"found {final_count:,}"
            )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Import Maharashtra village "
            "reference data."
        )
    )

    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_JSON_PATH,
        help=(
            "Path to the Maharashtra "
            "reference JSON file."
        ),
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help=(
            "Replace existing reference data."
        ),
    )

    args = parser.parse_args()

    records = load_records(args.file)

    import_records(
        records=records,
        replace=args.replace,
    )


if __name__ == "__main__":
    main()