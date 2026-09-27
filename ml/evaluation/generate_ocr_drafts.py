from __future__ import annotations

import argparse
from pathlib import Path

import pytesseract
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "rendered"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "ocr_drafts"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Tesseract OCR drafts for evaluation images."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--language",
        default="mar+eng",
        help="Tesseract language, e.g. mar, eng, or mar+eng.",
    )

    parser.add_argument(
        "--psm",
        type=int,
        default=4,
    )

    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.exists():
        raise FileNotFoundError(
            f"Input directory does not exist: {input_dir}"
        )

    image_files = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    )

    if not image_files:
        raise ValueError(
            f"No rendered evaluation images found in: {input_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Images found: {len(image_files)}")
    print(f"Language: {args.language}")
    print(f"PSM: {args.psm}")
    print()

    for image_path in image_files:
        with Image.open(image_path) as image:
            text = pytesseract.image_to_string(
                image,
                lang=args.language,
                config=f"--psm {args.psm}",
            )

        output_path = output_dir / f"{image_path.stem}.txt"
        output_path.write_text(
            text,
            encoding="utf-8",
        )

        print(f"Generated: {output_path.name}")

    print()
    print("OCR draft generation complete.")


if __name__ == "__main__":
    main()