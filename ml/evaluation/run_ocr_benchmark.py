from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class SampleResult:
    image: str
    reference: str
    prediction: str
    cer: float
    wer: float


def normalize_text(text: str) -> str:
    text = text.replace("\u200b", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def edit_distance(a: list[str], b: list[str]) -> int:
    previous = list(range(len(b) + 1))
    for i, token_a in enumerate(a, start=1):
        current = [i]
        for j, token_b in enumerate(b, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (token_a != token_b),
                )
            )
        previous = current
    return previous[-1]


def cer(reference: str, prediction: str) -> float:
    ref = list(normalize_text(reference))
    pred = list(normalize_text(prediction))
    if not ref:
        return 0.0 if not pred else 1.0
    return edit_distance(ref, pred) / len(ref)


def wer(reference: str, prediction: str) -> float:
    ref = normalize_text(reference).split()
    pred = normalize_text(prediction).split()
    if not ref:
        return 0.0 if not pred else 1.0
    return edit_distance(ref, pred) / len(ref)


def run_tesseract(image_path: Path, language: str, psm: int) -> str:
    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        language,
        "--psm",
        str(psm),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return completed.stdout


def load_manifest(path: Path) -> list[tuple[Path, str]]:
    rows: list[tuple[Path, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"image", "ground_truth"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Ground-truth CSV is missing columns: {', '.join(sorted(missing))}"
            )
        for row in reader:
            image = (row.get("image") or "").strip()
            truth = row.get("ground_truth") or ""
            if not image:
                continue
            rows.append((Path(image), truth))
    return rows


def evaluate(samples: Iterable[tuple[Path, str]], language: str, psm: int) -> dict:
    results: list[SampleResult] = []
    for image_path, reference in samples:
        prediction = run_tesseract(image_path, language, psm)
        results.append(
            SampleResult(
                image=str(image_path),
                reference=normalize_text(reference),
                prediction=normalize_text(prediction),
                cer=cer(reference, prediction),
                wer=wer(reference, prediction),
            )
        )

    if not results:
        raise ValueError("No evaluation samples were found.")

    return {
        "engine": "tesseract",
        "language": language,
        "psm": psm,
        "samples": len(results),
        "mean_cer": sum(r.cer for r in results) / len(results),
        "mean_wer": sum(r.wer for r in results) / len(results),
        "results": [asdict(r) for r in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Tesseract on an explicitly annotated OCR corpus."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/evaluation/ground_truth.csv"),
    )
    parser.add_argument(
        "--language",
        default="mar+eng",
    )
    parser.add_argument(
        "--psm",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/tesseract_benchmark.json"),
    )
    args = parser.parse_args()

    samples = load_manifest(args.manifest)
    resolved: list[tuple[Path, str]] = []
    for image_path, truth in samples:
        if not image_path.is_absolute():
            image_path = Path.cwd() / image_path
        if not image_path.exists():
            raise FileNotFoundError(f"Evaluation image not found: {image_path}")
        resolved.append((image_path, truth))

    report = evaluate(resolved, args.language, args.psm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Engine: {report['engine']}")
    print(f"Samples: {report['samples']}")
    print(f"Mean CER: {report['mean_cer']:.4f}")
    print(f"Mean WER: {report['mean_wer']:.4f}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
