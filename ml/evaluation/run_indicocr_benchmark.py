from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REPO = Path(
    r"C:\Users\sanskriti\.cache\huggingface\hub\models--bodhan-ai--indic-ocr\snapshots\cd50d301d0e17e8ecb32fc49c8ccbd7914dcfc25"
)

GROUND_TRUTH = (
    ROOT
    / "data"
    / "evaluation"
    / "field_ground_truth.csv"
)

OUTPUT = (
    ROOT
    / "data"
    / "evaluation"
    / "indicocr_field_benchmark.json"
)


def normalize(text: str) -> str:
    if not text:
        return ""

    text = text.strip().lower()

    devanagari = "०१२३४५६७८९"
    ascii_digits = "0123456789"

    text = text.translate(
        str.maketrans(
            devanagari,
            ascii_digits,
        )
    )

    return " ".join(text.split())


def load_ground_truth():
    with GROUND_TRUTH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def extract_text(result: dict) -> str:
    parts = []

    markdown = result.get("markdown")

    if markdown:
        parts.append(markdown)

    for block in result.get("blocks", []):
        text = block.get("text", "")

        if text:
            parts.append(text)

    return "\n".join(parts)


def main():

    print()
    print("BhoomiAI — IndicOCR Field Benchmark")
    print("------------------------------------")

    if not REPO.exists():
        raise FileNotFoundError(
            f"IndicOCR repository not found:\n{REPO}"
        )

    if not GROUND_TRUTH.exists():
        raise FileNotFoundError(
            f"Ground truth not found:\n{GROUND_TRUTH}"
        )

    sys.path.insert(
        0,
        str(REPO),
    )

    from indic_ocr import IndicOCR

    print("Loading IndicOCR...")

    start = time.perf_counter()

    parser = IndicOCR.from_pretrained(
        str(REPO)
    )

    load_seconds = (
        time.perf_counter()
        - start
    )

    print(
        f"Model loaded in {load_seconds:.1f}s"
    )

    rows = load_ground_truth()

    print(
        f"Samples: {len(rows)}"
    )

    results = []

    total_present = 0
    total_found = 0

    FIELD_NAMES = [
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

    field_stats = {
        field: {
            "evaluable": 0,
            "found": 0,
        }
        for field in FIELD_NAMES
    }

    total_inference_seconds = 0.0

    for i, row in enumerate(rows, start=1):

        image = (
            ROOT
            / row["image"]
        )

        print()
        print(
            f"[{i}/{len(rows)}] "
            f"{image.name}"
        )

        if not image.exists():
            print(
                "WARNING: image not found"
            )
            continue

        start = time.perf_counter()

        output = parser.parse(
            str(image)
        )

        seconds = (
            time.perf_counter()
            - start
        )

        total_inference_seconds += seconds

        text = extract_text(output)
        normalized_prediction = normalize(text)

        document = {
            "image": row["image"],
            "inference_seconds": round(
                seconds,
                2,
            ),
            "fields": {},
        }

        for field in FIELD_NAMES:

            status = (
                row.get(
                    f"{field}_status",
                    ""
                )
                or ""
            ).strip().lower()

            reference = (
                row.get(field, "")
                or ""
            ).strip()

            if (
                status != "present"
                or not reference
            ):
                continue

            ref = normalize(reference)

            found = (
                ref in normalized_prediction
            )

            field_stats[field]["evaluable"] += 1

            if found:
                field_stats[field]["found"] += 1

            total_present += 1

            if found:
                total_found += 1

            document["fields"][field] = {
                "reference": reference,
                "found_in_ocr": found,
            }

        results.append(document)

        print(
            f"  inference: {seconds:.1f}s"
        )

    summary = {}

    for field, stats in field_stats.items():

        n = stats["evaluable"]

        summary[field] = {
            "evaluable": n,
            "retrieval_recall": (
                round(
                    stats["found"] / n,
                    4,
                )
                if n
                else None
            ),
        }

    overall = {
        "evaluable_fields": total_present,
        "retrieved_fields": total_found,
        "field_retrieval_recall": (
            round(
                total_found / total_present,
                4,
            )
            if total_present
            else None
        ),
        "total_inference_seconds": round(
            total_inference_seconds,
            2,
        ),
        "average_inference_seconds": round(
            total_inference_seconds
            / len(results),
            2,
        )
        if results
        else None,
    }

    report = {
        "benchmark": "indicocr_field_retrieval",
        "engine": "IndicOCR",
        "language": "Marathi",
        "samples": len(rows),
        "overall": overall,
        "field_summary": summary,
        "documents": results,
    }

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("------------------------------------")
    print("Evaluable fields:", total_present)
    print(
        "Retrieved fields:",
        total_found,
    )
    print(
        "Field retrieval recall:",
        (
            f"{overall['field_retrieval_recall']:.4f}"
            if overall["field_retrieval_recall"] is not None
            else "N/A"
        ),
    )
    print(
        "Average inference:",
        overall["average_inference_seconds"],
        "seconds/page",
    )
    print()
    print("Per field:")

    for field, stats in summary.items():

        if stats["evaluable"]:

            print(
                f"  {field}: "
                f"n={stats['evaluable']} "
                f"recall={stats['retrieval_recall']:.4f}"
            )

    print()
    print("Report:")
    print(OUTPUT)
    print()
    print("DONE.")


if __name__ == "__main__":
    main()