from pathlib import Path
import json
import sys
import time

import torch


ROOT = Path(__file__).resolve().parents[2]

REPO = Path(
    r"C:\Users\sanskriti\.cache\huggingface\hub\models--bodhan-ai--indic-ocr\snapshots\cd50d301d0e17e8ecb32fc49c8ccbd7914dcfc25"
)

IMAGE = (
    ROOT
    / "data"
    / "evaluation"
    / "rendered"
    / "sampleimage1_page_01.png"
)

OUTPUT = (
    ROOT
    / "data"
    / "evaluation"
    / "indicocr_test_sample1.json"
)


def main():
    print()
    print("BhoomiAI — IndicOCR single-page test")
    print("--------------------------------------")

    print("Python:", sys.version.split()[0])
    print("PyTorch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())

    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
        print(
            "GPU memory:",
            round(
                torch.cuda.get_device_properties(0).total_memory
                / (1024 ** 3),
                2,
            ),
            "GB",
        )

    print("Repository:", REPO)
    print("Image:", IMAGE)

    if not REPO.exists():
        raise FileNotFoundError(
            f"IndicOCR repository not found: {REPO}"
        )

    if not IMAGE.exists():
        raise FileNotFoundError(
            f"Evaluation image not found: {IMAGE}"
        )

    sys.path.insert(0, str(REPO))

    print()
    print("Importing IndicOCR...")

    from indic_ocr import IndicOCR

    print("Import successful.")

    print()
    print("Loading IndicOCR...")
    print("This may take a while on the first run.")

    start = time.perf_counter()

    parser = IndicOCR.from_pretrained(
        str(REPO)
    )

    load_time = time.perf_counter() - start

    print(
        f"Model loaded in {load_time:.1f} seconds."
    )

    print()
    print("Running OCR on one page...")

    start = time.perf_counter()

    result = parser.parse(
        str(IMAGE)
    )

    inference_time = time.perf_counter() - start

    print(
        f"OCR completed in {inference_time:.1f} seconds."
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Result saved to:")
    print(OUTPUT)

    print()
    print("Recognized text:")
    print("--------------------------------------")

    print(
        result.get(
            "markdown",
            ""
        )
    )

    print("--------------------------------------")

    blocks = result.get(
        "blocks",
        []
    )

    print()
    print("Blocks detected:", len(blocks))

    if blocks:
        print()
        print("First 10 blocks:")

        for block in blocks[:10]:
            print(
                json.dumps(
                    block,
                    ensure_ascii=False,
                )
            )

    print()
    print("DONE.")


if __name__ == "__main__":
    main()