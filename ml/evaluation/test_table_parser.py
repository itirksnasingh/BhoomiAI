from html.parser import HTMLParser
import json
from pathlib import Path


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current_row = []

        elif tag in ("td", "th"):
            self.current_cell = []
            self.current_tag = tag

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            if self.current_row is not None:
                text = "".join(self.current_cell or [])
                text = " ".join(text.split())
                self.current_row.append({
                    "tag": self.current_tag,
                    "text": text,
                })

            self.current_cell = None
            self.current_tag = None

        elif tag == "tr":
            if self.current_row is not None:
                self.rows.append(self.current_row)
            self.current_row = None

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell.append(data)


def main():
    root = Path(__file__).resolve().parents[2]

    json_path = (
        root
        / "data"
        / "evaluation"
        / "indicocr_test_sample1.json"
    )

    data = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    table_blocks = [
        block
        for block in data.get("blocks", [])
        if block.get("type") == "Table"
    ]

    print()
    print("BhoomiAI — IndicOCR table parser test")
    print("--------------------------------------")
    print("Table blocks:", len(table_blocks))

    for index, block in enumerate(table_blocks, start=1):
        print()
        print(f"TABLE {index}")
        print("Block:", block.get("order"))
        print("Confidence:", block.get("conf"))
        print("BBox:", block.get("bbox_xyxy"))

        parser = TableParser()
        parser.feed(block.get("text", ""))

        print("Rows:", len(parser.rows))
        print()

        for row_number, row in enumerate(parser.rows, start=1):
            print(f"Row {row_number}:")
            for column_number, cell in enumerate(row, start=1):
                print(
                    f"  Col {column_number} "
                    f"[{cell['tag']}]: {cell['text']!r}"
                )

    print()
    print("DONE.")


if __name__ == "__main__":
    main()