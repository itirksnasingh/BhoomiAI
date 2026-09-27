# BhoomiAI — Final Phase 4 Accuracy Extraction Report

## Scope
- Unique raw IndicOCR documents processed: 4
- Ground-truth rows: 12
- Evaluable fields: 6
- Extracted-field coverage: 0.3333
- Exact field recall: 0.1667
- No OCR inference performed in this batch.
- Duplicate artifacts were collapsed by image basename.

## Field results
- **survey_gat_number** — evaluable 4; extracted 1; exact 1; coverage 0.25; exact recall 0.25; similarity 0.25
- **sub_division** — evaluable 0; extracted 0; exact 0; coverage None; exact recall None; similarity None
- **account_number** — evaluable 0; extracted 0; exact 0; coverage None; exact recall None; similarity None
- **holder_name** — evaluable 0; extracted 0; exact 0; coverage None; exact recall None; similarity None
- **cultivable_area** — evaluable 0; extracted 0; exact 0; coverage None; exact recall None; similarity None
- **land_tenure** — evaluable 1; extracted 1; exact 0; coverage 1.0; exact recall 0.0; similarity 0.0
- **local_field_name** — evaluable 1; extracted 0; exact 0; coverage 0.0; exact recall 0.0; similarity 0.0

## Failure cases
- `sampleimage10_page_01.png` / `survey_gat_number` — GT `48`; prediction ``; similarity 0.0
- `sampleimage12_page_01.png` / `survey_gat_number` — GT `92`; prediction ``; similarity 0.0
- `sampleimage12_page_01.png` / `land_tenure` — GT `कोरडवाहू`; prediction `-`; similarity 0.0
- `sampleimage12_page_01.png` / `local_field_name` — GT `सिरगाव`; prediction ``; similarity 0.0
- `sampleimage1_page_01.png` / `survey_gat_number` — GT `48`; prediction ``; similarity 0.0


## Phase 4 closure
This report separates extraction coverage from exact accuracy and does not treat unavailable ground-truth fields as failures. Any future OCR/model work belongs to a later phase or a separately defined benchmark expansion.
