from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path


MARATHI_DIGITS = str.maketrans(
    "०१२३४५६७८९",
    "0123456789",
)


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_digits(text: str) -> str:
    return text.translate(MARATHI_DIGITS)


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current_row = []

        elif tag in ("td", "th"):
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            if self.current_row is not None:
                text = normalize_text(
                    "".join(self.current_cell or [])
                )

                self.current_row.append(text)

            self.current_cell = None

        elif tag == "tr":
            if self.current_row is not None:
                self.rows.append(self.current_row)

            self.current_row = None

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell.append(data)


def parse_table(html: str) -> list[list[str]]:
    parser = TableParser()
    parser.feed(html)
    return parser.rows


def find_main_land_table(blocks):
    """
    Find the main 7/12 land-record table.

    We deliberately avoid using every Table block because
    7/12 pages can contain crop-record tables as well.
    """
    candidates = []

    for block in blocks:
        if block.get("type") != "Table":
            continue

        text = block.get("text", "")

        score = 0

        if "भूमापन क्रमांक" in text:
            score += 5

        if "भू-धारणा" in text:
            score += 4

        if "खाते क्रमांक" in text:
            score += 3

        if "शेताचे स्थानिक नाव" in text:
            score += 3

        if "भोगवटादार" in text:
            score += 2

        candidates.append((score, block))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return candidates[0][1]


def extract_seven_twelve(blocks):
    table_block = find_main_land_table(blocks)

    result = {
        "document_type": "7/12",
        "source_block": None,
        "fields": {},
    }

    if table_block is None:
        return result

    result["source_block"] = table_block.get("order")

    rows = parse_table(
        table_block.get("text", "")
    )

    if not rows:
        return result

    # ---------------------------------------------------------
    # Survey number
    # ---------------------------------------------------------

    if len(rows) >= 2 and len(rows[1]) >= 1:
        survey = normalize_digits(rows[1][0])

        if survey and survey not in ("-", "."):
            result["fields"]["survey_number"] = {
                "value": survey,
                "confidence": table_block.get("conf"),
                "source_block": table_block.get("order"),
            }

    # ---------------------------------------------------------
    # Subdivision
    # ---------------------------------------------------------

    if len(rows) >= 2 and len(rows[1]) >= 2:
        subdivision = rows[1][1]

        if subdivision:
            result["fields"]["subdivision"] = {
                "value": subdivision,
                "confidence": table_block.get("conf"),
                "source_block": table_block.get("order"),
            }

    # ---------------------------------------------------------
    # Land tenure
    # ---------------------------------------------------------

    if len(rows) >= 2 and len(rows[1]) >= 3:
        tenure = rows[1][2]

        if tenure:
            result["fields"]["land_tenure"] = {
                "value": tenure,
                "confidence": table_block.get("conf"),
                "source_block": table_block.get("order"),
            }

    # ---------------------------------------------------------
    # Local field name
    # ---------------------------------------------------------

    for row in rows:
        if not row:
            continue

        first_cell = row[0]

        if "शेताचे स्थानिक नाव" in first_cell:
            result["fields"]["local_field_name"] = {
                "value": None,
                "confidence": table_block.get("conf"),
                "source_block": table_block.get("order"),
                "status": "label_found_value_not_resolved",
            }

            break

    return result


def main():
    root = Path(__file__).resolve().parents[2]

    input_path = (
        root
        / "data"
        / "evaluation"
        / "indicocr_test_sample1.json"
    )

    data = json.loads(
        input_path.read_text(
            encoding="utf-8"
        )
    )

    result = extract_seven_twelve(
        data.get("blocks", [])
    )

    print()
    print("BhoomiAI — 7/12 extraction prototype")
    print("--------------------------------------")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )
    print()
    print("DONE.")


if __name__ == "__main__":
    main()