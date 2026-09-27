from __future__ import annotations

import compileall
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
SMOKE = BACKEND / "scripts" / "phase5_smoke_test.py"


def main() -> int:
    print("=== BhoomiAI Phase 5 — Production Extraction + Verification ===")
    print(f"Repository: {ROOT}")
    print()

    print("[1/3] Compiling backend Python files...")
    if not compileall.compile_dir(str(BACKEND / "app"), quiet=1):
        print("PHASE 5: FAIL — backend compilation failed.")
        return 1
    print("  Backend compilation: PASS")

    print("[2/3] Running production extraction smoke test...")
    if not SMOKE.exists():
        print(f"PHASE 5: FAIL — smoke test missing: {SMOKE}")
        return 1

    result = subprocess.run(
        [sys.executable, str(SMOKE)],
        cwd=str(BACKEND),
        env={**os.environ, "PYTHONPATH": str(BACKEND)},
    )
    if result.returncode != 0:
        print("PHASE 5: FAIL — smoke test failed.")
        return result.returncode

    print("[3/3] Verifying Phase 5 artifacts...")
    required = [
        SMOKE,
        BACKEND / "app/services/extraction/seven_twelve_table.py",
        BACKEND / "app/services/extraction/types.py",
        BACKEND / "app/services/extraction/field_extractor.py",
        BACKEND / "app/services/extraction/extraction_service.py",
        BACKEND / "app/services/validation/rules.py",
        ROOT / "docs/architecture/phase-5-production-extraction.md",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("PHASE 5: FAIL — missing artifacts:")
        for path in missing:
            print(" -", path)
        return 1

    print("  Artifact verification: PASS")
    print()
    print("=== PHASE 5 BATCH COMPLETE ===")
    print("Production 7/12 table-aware extraction: READY")
    print("Evidence-linked extraction: READY")
    print("Validation integration: READY")
    print("NO OCR MODEL TRAINING OR NEW OCR INFERENCE WAS RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
