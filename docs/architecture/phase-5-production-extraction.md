# BhoomiAI Phase 5 — Production Extraction + Verification

## Objective

Phase 5 integrates the table-aware 7/12 land-record extraction pipeline into the production BhoomiAI extraction service.

The phase builds on the Phase 4 OCR and extraction evaluation work and moves the successful 7/12 table parsing logic into the production extraction layer.

## Production Flow

READ → VERIFY → TRUST

1. Document is uploaded.
2. OCR produces text blocks and spatial evidence.
3. 7/12 table-aware extraction identifies structured fields.
4. Extracted values are normalized.
5. Evidence bounding boxes/blocks remain linked to extracted fields.
6. Validation rules can evaluate the extracted values.
7. The resulting fields can be consumed by the existing BhoomiAI review and verification workflow.

## Supported 7/12 Fields

The Phase 5 production table extractor currently supports:

- Survey number / Gat number
- Subdivision
- Land tenure
- Owner name
- Khata number
- Local field name
- Area

## Evidence Linking

Each extracted field is associated with OCR evidence where available.

Evidence linkage allows the application to retain:

- OCR block identity
- Bounding-box information
- Extraction method
- Field confidence

This supports later human verification and auditability.

## Extraction Strategy

The production extractor uses table-aware processing rather than treating the entire 7/12 document as unstructured text.

The extraction process:

1. Identifies relevant 7/12 table content.
2. Parses table rows and cells.
3. Matches known Marathi/English field labels.
4. Resolves values using row and spatial relationships.
5. Normalizes extracted values.
6. Preserves explicit values such as `-` for subdivision when that value is present in the source.
7. Returns evidence-linked field results.

The extractor is intentionally conservative and prioritizes precision over speculative extraction.

## Validation

Phase 5 compiles the 7/12 validation rules used by the production extraction workflow.

Validation is separate from OCR and extraction so that extracted values can be checked independently of how they were obtained.

## Verification

The Phase 5 production smoke test verifies:

- Table-aware extraction
- Expected 7/12 field extraction
- Evidence-linked extraction
- 7/12 validation rule compilation
- Integration with the production `FieldExtractor`

The smoke test successfully extracts seven table-aware fields:

- area
- khata_number
- land_tenure
- local_field_name
- owner
- subdivision
- survey_number

## Phase 5 Status

Phase 5 implementation smoke test:

**PASS**

The production extraction integration is therefore ready for the next integration/verification stage.

## Relationship to Phase 4

Phase 4 established the OCR evaluation and extraction baseline.

Phase 5 moves the validated table-aware extraction approach into the production extraction service.

The Phase 4 accuracy results should not be interpreted as production accuracy for the complete BhoomiAI system. Phase 5 focuses on production extraction integration and verification.

## Next Stage

The next stage is end-to-end backend integration verification:

- FastAPI application startup
- database/model integration
- document processing flow
- production extraction persistence
- validation persistence
- evidence linkage
- review/audit workflow
