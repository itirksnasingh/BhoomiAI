from __future__ import annotations

import argparse
from pathlib import Path

import fitz  # PyMuPDF


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "images"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "rendered"


def render_pdf(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    document = fitz.open(pdf_path)
    rendered: list[Path] = []

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    try:
        for page_index, page in enumerate(document):
            image_path = (
                output_dir
                / f"{pdf_path.stem}_page_{page_index + 1:02d}.png"
            )

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            pixmap.save(image_path)
            rendered.append(image_path)

    finally:
        document.close()

    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render evaluation PDFs into PNG page images."
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
        "--dpi",
        type=int,
        default=200,
    )

    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.exists():
        raise FileNotFoundError(
            f"Evaluation directory does not exist: {input_dir}"
        )

    pdf_files = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )

    if not pdf_files:
        raise ValueError(
            f"No PDF evaluation samples found in: {input_dir}"
        )

    total_pages = 0

    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"PDFs found: {len(pdf_files)}")
    print()

    for pdf_path in pdf_files:
        rendered = render_pdf(
            pdf_path,
            output_dir,
            dpi=args.dpi,
        )

        total_pages += len(rendered)

        print(
            f"{pdf_path.name}: "
            f"{len(rendered)} page(s) rendered"
        )

    print()
    print("Rendering complete.")
    print(f"PDF samples: {len(pdf_files)}")
    print(f"Rendered pages: {total_pages}")
    print(f"Images: {output_dir}")


if __name__ == "__main__":
    main()