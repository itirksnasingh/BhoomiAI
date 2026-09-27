# BhoomiAI Phase 4 — Final Cache-First Evaluation

**Status:** CACHE-FIRST COMPLETE
**Samples:** 12

## Why this run is safe and fast
- Reuses the existing 12-page IndicOCR benchmark instead of launching another expensive model run.
- Uses the existing raw IndicOCR JSON for Sample 1 to verify table detection and the corrected survey number 48.
- Runs fresh Tesseract baselines locally.
- No optional optimized-kernel installation is required.

## Tesseract results
### PSM 4
- Exact field recall: **0.0385**
- Fuzzy field recall: **0.0385**
- Mean field similarity: **0.0879**

### PSM 6
- Exact field recall: **0.1538**
- Fuzzy field recall: **0.0**
- Mean field similarity: **0.0204**

### PSM 11
- Exact field recall: **0.1538**
- Fuzzy field recall: **0.0**
- Mean field similarity: **0.0126**

## Existing IndicOCR benchmark

- Historical evaluable fields: **25**
- Historical cached field retrieval recall: **0.2**
- Historical inference time: **2349.27 seconds total**

## Corrected-ground-truth caveat
- The legacy IndicOCR benchmark was produced before the confirmed Sample 1 and Sample 11 ground-truth corrections. It is therefore retained as a cached baseline, not presented as the final corrected 12-page accuracy score.
- Cached pages available: **12/12**.
- Pages requiring fresh IndicOCR inference for a fully corrected 12-page score: **0**.

## Sample 1 structure-aware proof
- Detected table blocks: **1**.
- The existing raw IndicOCR artifact contains the 7/12 table and survey value ४८.
- Table-aware parsing and Marathi digit normalization are included in the evaluation engine.

## Interpretation
- This Phase 4 batch is intentionally cache-first so it does not unexpectedly consume ~40 minutes of GPU inference.
- A fully corrected 12-page IndicOCR score requires fresh inference for the pages listed in `indicocr_cached_analysis.json`.
- Do not interpret the legacy 20% recall as the final model accuracy.
