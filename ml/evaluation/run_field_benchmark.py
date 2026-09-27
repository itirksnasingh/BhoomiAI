from __future__ import annotations

import argparse
import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import pytesseract
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CSV = ROOT / "data" / "evaluation" / "field_ground_truth.csv"
DEFAULT_OUTPUT = ROOT / "data" / "evaluation" / "tesseract_field_benchmark.json"


FIELDS = [
    "document_type",
    "village",
    "taluka",
    "survey_gat_number",
    "sub_division",
    "account_number",
    "holder_name",
    "cultivable_area",
    "land_tenure",
    "local_field_name",
]


def normalize_text(value: str) -> str:
    if not value:
        return ""

    text = value.strip().lower()

    # Convert Devanagari digits to ASCII digits.
    devanagari_digits = "०१२३४५६७८९"
    ascii_digits = "0123456789"

    translation = str.maketrans(
        devanagari_digits,
        ascii_digits,
    )

    text = text.translate(translation)

    # Normalize common dash variants.
    text = re.sub(r"[–—−]", "-", text)

    # Remove punctuation while keeping letters and numbers.
    text = re.sub(
        r"[^\w\s\u0900-\u097F/-]",
        " ",
        text,
        flags=re.UNICODE,
    )

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def similarity(reference: str, prediction: str) -> float:
    ref = normalize_text(reference)
    pred = normalize_text(prediction)

    if not ref:
        return 0.0

    if ref in pred:
        return 1.0

    return SequenceMatcher(
        None,
        ref,
        pred,
    ).ratio()


def read_ground_truth(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        return list(csv.DictReader(file))


def get_image_path(relative_path: str) -> Path:
    path = ROOT / relative_path

    if path.exists():
        return path

    # Fallback for malformed/absolute-style entries.
    filename = Path(relative_path).name

    fallback = (
        ROOT
        / "data"
        / "evaluation"
        / "rendered"
        / filename
    )

    return fallback


def is_evaluable(row: dict[str, str], field: str) -> bool:
    status = (
        row.get(f"{field}_status") or ""
    ).strip().lower()

    value = (
        row.get(field) or ""
    ).strip()

    return (
        status == "present"
        and bool(value)
    )


def benchmark(
    csv_path: Path,
    output_path: Path,
    psm: int,
) -> None:

    rows = read_ground_truth(csv_path)

    if not rows:
        raise RuntimeError(
            "Ground-truth CSV contains no rows."
        )

    field_results = {
        field: {
            "evaluable": 0,
            "found_exact": 0,
            "found_fuzzy": 0,
            "similarity_sum": 0.0,
        }
        for field in FIELDS
    }

    document_results = []

    total_evaluable = 0
    total_exact = 0
    total_fuzzy = 0
    total_similarity = 0.0

    for row in rows:

        image_path = get_image_path(
            row["image"]
        )

        if not image_path.exists():
            print(
                f"WARNING: image not found: {image_path}"
            )
            continue

        with Image.open(image_path) as image:

            prediction = pytesseract.image_to_string(
                image,
                lang="mar+eng",
                config=f"--psm {psm}",
            )

        normalized_prediction = normalize_text(prediction)

        document = {
            "image": row["image"],
            "fields": {},
        }

        for field in FIELDS:

            if not is_evaluable(row, field):
                continue

            reference = (
                row.get(field) or ""
            ).strip()

            ref_norm = normalize_text(
                reference
            )

            exact = (
                ref_norm in normalized_prediction
                if ref_norm
                else False
            )

            score = similarity(
                reference,
                prediction,
            )

            fuzzy = score >= 0.80

            field_results[field]["evaluable"] += 1

            if exact:
                field_results[field]["found_exact"] += 1

            if fuzzy:
                field_results[field]["found_fuzzy"] += 1

            field_results[field]["similarity_sum"] += score

            total_evaluable += 1
            total_similarity += score

            if exact:
                total_exact += 1

            if fuzzy:
                total_fuzzy += 1

            document["fields"][field] = {
                "reference": reference,
                "exact_found_in_ocr": exact,
                "fuzzy_match": fuzzy,
                "similarity": round(score, 4),
            }

        document_results.append(document)


    field_summary = {}

    for field, result in field_results.items():

        evaluable = result["evaluable"]

        if evaluable == 0:
            field_summary[field] = {
                "evaluable": 0,
                "exact_recall": None,
                "fuzzy_recall": None,
                "mean_similarity": None,
            }

            continue

        field_summary[field] = {
            "evaluable": evaluable,
            "exact_recall": round(
                result["found_exact"] / evaluable,
                4,
            ),
            "fuzzy_recall": round(
                result["found_fuzzy"] / evaluable,
                4,
            ),
            "mean_similarity": round(
                result["similarity_sum"] / evaluable,
                4,
            ),
        }


    overall = {
        "evaluable_fields": total_evaluable,
        "exact_field_recall": (
            round(
                total_exact / total_evaluable,
                4,
            )
            if total_evaluable
            else None
        ),
        "fuzzy_field_recall": (
            round(
                total_fuzzy / total_evaluable,
                4,
            )
            if total_evaluable
            else None
        ),
        "mean_field_similarity": (
            round(
                total_similarity / total_evaluable,
                4,
            )
            if total_evaluable
            else None
        ),
    }


    report = {
        "benchmark": "tesseract_field_visibility",
        "engine": "tesseract",
        "language": "mar+eng",
        "psm": psm,
        "samples": len(rows),
        "overall": overall,
        "field_summary": field_summary,
        "documents": document_results,
    }


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print("BhoomiAI Field OCR Benchmark")
    print("--------------------------------")
    print("Engine:", "tesseract")
    print("Language:", "mar+eng")
    print("PSM:", psm)
    print("Samples:", len(rows))
    print()

    print(
        "Evaluable fields:",
        total_evaluable,
    )

    print(
        "Exact field recall:",
        (
            f"{overall['exact_field_recall']:.4f}"
            if overall["exact_field_recall"] is not None
            else "N/A"
        ),
    )

    print(
        "Fuzzy field recall:",
        (
            f"{overall['fuzzy_field_recall']:.4f}"
            if overall["fuzzy_field_recall"] is not None
            else "N/A"
        ),
    )

    print(
        "Mean field similarity:",
        (
            f"{overall['mean_field_similarity']:.4f}"
            if overall["mean_field_similarity"] is not None
            else "N/A"
        ),
    )

    print()

    print("Per-field:")

    for field, summary in field_summary.items():

        if summary["evaluable"] == 0:
            continue

        print(
            f"  {field}: "
            f"n={summary['evaluable']} "
            f"exact={summary['exact_recall']:.4f} "
            f"fuzzy={summary['fuzzy_recall']:.4f} "
            f"sim={summary['mean_similarity']:.4f}"
        )

    print()
    print("Report:", output_path)
    print()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
    )

    parser.add_argument(
        "--psm",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    benchmark(
        csv_path=args.csv,
        output_path=args.output,
        psm=args.psm,
    )


if __name__ == "__main__":
    main()