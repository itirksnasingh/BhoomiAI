# BhoomiAI Phase 4 — Maharashtra OCR/HTR Evaluation

## Goal

Benchmark OCR/HTR candidates against an explicitly annotated corpus instead of claiming accuracy from OCR engine confidence.

## Evaluation corpus

The final corpus should contain legally usable or authorized Maharashtra land-record samples, starting with the primary MVP document type (7/12) and expanding only when sufficient data exists.

Each sample should record:

- image path
- document type
- page number
- ground-truth text
- language/script
- printed vs handwritten indicator
- document quality metadata
- optional field annotations for field-level F1

Synthetic documents may be used for pipeline tests and controlled degradation experiments, but they must not be presented as the final Maharashtra benchmark corpus.

## Metrics

Text recognition:

- Character Error Rate (CER)
- Word Error Rate (WER)

Structured extraction:

- field-level precision, recall and F1
- exact-match rate for critical identifiers such as survey/gat numbers

Operational:

- processing time per page
- failure rate
- safe-review rate after confidence calibration

## Candidate ladder

1. Tesseract `mar+eng` with BhoomiAI preprocessing.
2. Alternative Tesseract page segmentation modes where beneficial.
3. PaddleOCR/Indic OCR candidate after environment compatibility is confirmed.
4. Indic/Devanagari TrOCR-style recognition for line/region crops.
5. Fine-tuned candidate only after enough labeled Maharashtra data exists.

Do not select a model from generic leaderboard claims. Select it from measured results on the project corpus.

## Current data rule

No final accuracy number should be reported until the ground-truth manifest contains real annotated samples. An empty template is intentionally provided so the benchmark cannot accidentally manufacture a metric.
