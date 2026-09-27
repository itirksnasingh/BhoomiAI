# OCR Evaluation Harness

Run from the BhoomiAI repository root.

## Manifest

Populate `data/evaluation/ground_truth.csv` with:

```csv
image,ground_truth
"data/evaluation/images/sample001.png","मराठी मजकूर"
```

The image must already exist at the given path and the ground truth must be manually verified.

## Tesseract baseline

```powershell
python ml\evaluation\run_ocr_benchmark.py --manifest data\evaluation\ground_truth.csv --language mar+eng --psm 6
```

Try the main page-segmentation modes:

```powershell
python ml\evaluation\run_ocr_benchmark.py --psm 4 --output data\evaluation\tesseract_psm4.json
python ml\evaluation\run_ocr_benchmark.py --psm 6 --output data\evaluation\tesseract_psm6.json
python ml\evaluation\run_ocr_benchmark.py --psm 11 --output data\evaluation\tesseract_psm11.json
```

Lower CER/WER is better.

No model should be called more accurate based only on OCR confidence. The ground truth is the source of truth for this benchmark.
