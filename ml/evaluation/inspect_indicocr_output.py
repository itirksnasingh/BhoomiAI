from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]

TEST_FILE = (
    ROOT
    / "data"
    / "evaluation"
    / "indicocr_test_sample1.json"
)


def main():
    if not TEST_FILE.exists():
        print("ERROR: Result file not found:")
        print(TEST_FILE)
        return

    data = json.loads(
        TEST_FILE.read_text(
            encoding="utf-8"
        )
    )

    print()
    print("IndicOCR output inspection")
    print("==========================")
    print()

    print("Image:")
    print(data.get("image"))
    print()

    print("Page size:")
    print(
        data.get("width"),
        "x",
        data.get("height")
    )
    print()

    blocks = data.get("blocks", [])

    print("Blocks:", len(blocks))
    print()

    for i, block in enumerate(blocks, start=1):

        print(
            f"BLOCK {i}"
        )
        print(
            "  order:",
            block.get("order")
        )
        print(
            "  label:",
            block.get("label")
        )
        print(
            "  type:",
            block.get("type")
        )
        print(
            "  confidence:",
            block.get("conf")
        )
        print(
            "  bbox:",
            block.get("bbox_xyxy")
        )

        text = block.get("text", "")

        print("  text:")

        if text:
            print(text[:500])
        else:
            print("(empty)")

        print("-" * 70)

    print()
    print("Full Markdown preview")
    print("=====================")
    print()

    markdown = data.get(
        "markdown",
        ""
    )

    print(
        markdown[:10000]
    )

    print()
    print("DONE.")


if __name__ == "__main__":
    main()