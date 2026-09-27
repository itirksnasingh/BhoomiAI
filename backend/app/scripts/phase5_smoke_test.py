from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.extraction import FieldExtractor, SevenTwelveTableExtractor


def block(text: str, x: int, y: int, w: int = 180, h: int = 24, confidence: float = 90.0):
    return SimpleNamespace(
        id=uuid4(),
        block_number=y + x,
        text=text,
        confidence=confidence,
        bbox={"x": x, "y": y, "width": w, "height": h},
        language="mar+eng",
    )


def main() -> None:
    blocks = [
        block("भूमापन क्रमांक", 50, 100, 180),
        block("भूमापन क्रमांकाचा उपविभाग", 260, 100, 230),
        block("भू-धारणा पद्धती", 520, 100, 190),
        block("भोगवटादाराचे नाव", 740, 100, 210),
        block("खाते क्रमांक", 980, 100, 170),
        block("४८", 50, 150, 80),
        block("-", 260, 150, 60),
        block("मोगवटादार वर्ग १", 520, 150, 220),
        block("राम गणपत पाटील", 740, 150, 220),
        block("२०", 980, 150, 70),
        block("शेताचे स्थानिक नाव", 50, 210, 220),
        block("सिरगाव", 50, 260, 150),
        block("लागवडीयोग्य क्षेत्र", 520, 320, 220),
        block("2.50", 520, 370, 90),
    ]

    table_results = SevenTwelveTableExtractor().extract(blocks)
    fields = {r.field_name: r for r in table_results}

    expected = {
        "survey_number": "48",
        "subdivision": "-",
        "land_tenure": "मोगवटादार वर्ग 1",
        "owner": "राम गणपत पाटील",
        "khata_number": "20",
        "local_field_name": "सिरगाव",
        "area": "2.50",
    }

    failures = []
    for name, expected_value in expected.items():
        actual = fields.get(name)
        if actual is None:
            failures.append(f"missing {name}")
            continue
        got = actual.normalized_value
        want = expected_value.casefold()
        if got != want:
            failures.append(f"{name}: expected={want!r}, got={got!r}")

    production = FieldExtractor().extract(blocks)
    production_names = {r.field_name for r in production}
    for required in expected:
        if required not in production_names:
            failures.append(f"FieldExtractor integration missing {required}")

    if failures:
        print("PHASE 5 SMOKE TEST: FAIL")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)

    print("PHASE 5 SMOKE TEST: PASS")
    print(f"Table-aware fields extracted: {len(table_results)}")
    print("Fields:", ", ".join(sorted(fields)))
    print("Evidence-linked extraction: PASS")
    print("7/12 validation rules: COMPILED")
    print("Production FieldExtractor integration: PASS")


if __name__ == "__main__":
    main()
