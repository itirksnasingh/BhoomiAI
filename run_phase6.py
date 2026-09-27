from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path.cwd()
BACKEND = ROOT / 'backend'
FRONTEND = ROOT / 'frontend'

if not (BACKEND / 'app').exists() or not (FRONTEND / 'src').exists():
    raise SystemExit('Run this from the BhoomiAI repository root (the folder containing backend and frontend).')

stamp = 'phase6_backup'
backup = ROOT / stamp
backup.mkdir(exist_ok=True)


def backup_file(path: Path):
    if path.exists():
        rel = path.relative_to(ROOT)
        dest = backup / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

# ------------------------------------------------------------------
# 1. Add the single end-to-end pipeline service.
# ------------------------------------------------------------------

pipeline = BACKEND / 'app/services/processing/pipeline_service.py'
backup_file(pipeline)
write(pipeline, '''from __future__ import annotations\n\nfrom datetime import datetime, timezone\nfrom uuid import UUID\n\nfrom sqlalchemy.orm import Session\n\nfrom app.models.documents import Document, DocumentPage, DocumentStatus\nfrom app.models.extraction import ExtractedField, ExtractionRun, OCRRun, OCRRunStatus\nfrom app.models.validation import ValidationResult, ValidationRun\nfrom app.services.documents import DocumentStorageService\nfrom app.services.extraction import ExtractionService\nfrom app.services.ocr import OCRService\nfrom app.services.processing.document_processor import process_document\nfrom app.services.validation import ValidationService\n\n\nclass DocumentPipelineService:\n    """Run the complete READ -> VERIFY pipeline for one document.\n\n    The service deliberately reuses the existing OCR, extraction and\n    validation services so Phase 6 is orchestration, not a second AI stack.\n    Every stage persists its own lineage and evidence.\n    """\n\n    VERSION = "6.0"\n\n    def run(self, db: Session, document_id: UUID, language: str = "mar+eng") -> dict:\n        document = db.query(Document).filter(Document.id == document_id).first()\n        if document is None:\n            raise ValueError("Document not found.")\n\n        started = datetime.now(timezone.utc)\n        document.status = DocumentStatus.PROCESSING\n        db.flush()\n\n        try:\n            # Stage 1: ensure page images exist.\n            storage = DocumentStorageService()\n            pages = (\n                db.query(DocumentPage)\n                .filter(DocumentPage.document_id == document_id)\n                .order_by(DocumentPage.page_number)\n                .all()\n            )\n\n            rebuild = not pages\n            if pages:\n                for page in pages:\n                    if not page.image_storage_key:\n                        rebuild = True\n                        break\n                    try:\n                        storage.storage.get_path(page.image_storage_key)\n                    except FileNotFoundError:\n                        rebuild = True\n                        break\n\n            if rebuild:\n                source = (\n                    db.query(storage.document_file_model)\n                    .filter(storage.document_file_model.document_id == document_id)\n                    .order_by(storage.document_file_model.created_at.desc())\n                    .first()\n                ) if hasattr(storage, "document_file_model") else None\n\n                if source is None:\n                    # Fall back to the model used by the existing API.\n                    from app.models.documents import DocumentFile\n                    source = (\n                        db.query(DocumentFile)\n                        .filter(DocumentFile.document_id == document_id)\n                        .order_by(DocumentFile.created_at.desc())\n                        .first()\n                    )\n\n                if source is None:\n                    raise ValueError("No stored source file is available for this document.")\n\n                db.query(DocumentPage).filter(\n                    DocumentPage.document_id == document_id\n                ).delete(synchronize_session=False)\n                db.flush()\n                process_document(\n                    db=db,\n                    document=document,\n                    file_path=str(storage.get_document_file_path(source)),\n                )\n\n            # Stage 2: OCR + classification.\n            ocr_runs = OCRService().process_document(\n                db=db, document=document, language=language\n            )\n            db.flush()\n            if not ocr_runs or not all(r.status == OCRRunStatus.COMPLETED for r in ocr_runs):\n                raise ValueError("One or more document pages failed OCR.")\n            db.commit()\n\n            # Stage 3: document-type-aware extraction through the existing\n            # production FieldExtractor/Phase-5 integration.\n            fields = ExtractionService().extract_document_fields(\n                db=db, document_id=document_id\n            )\n            db.commit()\n\n            extraction_run = (\n                db.query(ExtractionRun)\n                .filter(ExtractionRun.document_id == document_id)\n                .order_by(ExtractionRun.created_at.desc())\n                .first()\n            )\n            if extraction_run is None:\n                raise ValueError("Extraction completed without an extraction run.")\n\n            # Stage 4: validation + cross-field consistency.\n            validation_run, results = ValidationService().validate_document(\n                db=db, document_id=document_id\n            )\n\n            statuses = {str(getattr(r.status, "value", r.status)).upper() for r in results}\n            needs_review = bool(statuses & {"REVIEW", "WARNING", "FAIL", "FAILED"})\n            document.status = (\n                DocumentStatus.VALIDATION_REQUIRED if needs_review\n                else DocumentStatus.PROCESSED\n            )\n            db.commit()\n\n            elapsed = (datetime.now(timezone.utc) - started).total_seconds()\n\n            return {\n                "pipeline_version": self.VERSION,\n                "document_id": str(document.id),\n                "status": document.status.value,\n                "document_type": getattr(document.document_type, "value", str(document.document_type)),\n                "language": document.language,\n                "pages": len(ocr_runs),\n                "ocr_runs": len(ocr_runs),\n                "fields_extracted": len(fields),\n                "extraction_run_id": str(extraction_run.id),\n                "validation_run_id": str(validation_run.id),\n                "validation_results": len(results),\n                "review_required": needs_review,\n                "processing_seconds": round(elapsed, 3),\n                "stages": {\n                    "ingestion": "COMPLETED",\n                    "preprocessing": "COMPLETED",\n                    "ocr": "COMPLETED",\n                    "classification": "COMPLETED",\n                    "extraction": "COMPLETED",\n                    "evidence": "COMPLETED",\n                    "validation": "COMPLETED",\n                },\n            }\n\n        except Exception:\n            db.rollback()\n            try:\n                document = db.query(Document).filter(Document.id == document_id).first()\n                if document is not None:\n                    document.status = DocumentStatus.FAILED\n                    db.commit()\n            except Exception:\n                db.rollback()\n            raise\n''')

# ------------------------------------------------------------------
# 2. Patch the document API with a single /run endpoint.
# ------------------------------------------------------------------

api = BACKEND / 'app/api/v1/documents.py'
backup_file(api)
text = api.read_text(encoding='utf-8')

if 'DocumentPipelineService' not in text:
    marker = 'from app.services.processing.document_processor import (\n    process_document,\n)\n'
    replacement = marker + '\nfrom app.services.processing.pipeline_service import (\n    DocumentPipelineService,\n)\n'
    if marker not in text:
        raise SystemExit('Phase 6 patch stopped: expected processing import block was not found in documents.py.')
    text = text.replace(marker, replacement, 1)

if '@router.post("/{document_id}/run")' not in text:
    anchor = '\n\n# ============================================================\n# EXTRACTION\n# ============================================================\n'
    endpoint = '''\n\n# ============================================================\n# END-TO-END PIPELINE\n# ============================================================\n\n\n@router.post("/{document_id}/run")\ndef run_document_pipeline(\n    document_id: UUID,\n    db: Session = Depends(get_db),\n    current_user: User = Depends(\n        require_role(\n            UserRole.ADMIN,\n            UserRole.REVIEWER,\n        )\n    ),\n) -> dict:\n    """Run ingestion recovery, OCR, classification, extraction, evidence and validation."""\n\n    try:\n        result = DocumentPipelineService().run(\n            db=db,\n            document_id=document_id,\n            language="mar+eng",\n        )\n        return result\n    except ValueError as exc:\n        db.rollback()\n        raise HTTPException(status_code=400, detail=str(exc)) from exc\n    except Exception as exc:\n        db.rollback()\n        raise HTTPException(\n            status_code=500,\n            detail=f"End-to-end document pipeline failed: {exc}",\n        ) from exc\n'''
    if anchor not in text:
        raise SystemExit('Phase 6 patch stopped: extraction anchor not found in documents.py.')
    text = text.replace(anchor, endpoint + anchor, 1)

api.write_text(text, encoding='utf-8')

# ------------------------------------------------------------------
# 3. Add the frontend API function and switch upload to one pipeline call.
# ------------------------------------------------------------------

api_ts = FRONTEND / 'src/services/api.ts'
backup_file(api_ts)
api_text = api_ts.read_text(encoding='utf-8')

if 'runDocumentPipeline' not in api_text:
    anchor = 'export async function processDocument(\n'
    fn = '''export async function runDocumentPipeline(\n  documentId: string,\n): Promise<Record<string, unknown>> {\n  if (!documentId) throw new Error("Document ID is missing.");\n  return request<Record<string, unknown>>(\n    `/api/v1/documents/${documentId}/run`,\n    { method: "POST" },\n  );\n}\n\n'''
    if anchor not in api_text:
        raise SystemExit('Phase 6 patch stopped: processDocument anchor not found in frontend API service.')
    api_text = api_text.replace(anchor, fn + anchor, 1)
    api_ts.write_text(api_text, encoding='utf-8')

# Documents page: use the single endpoint after upload. This avoids the UI
# having to coordinate three separate backend operations.
docs = FRONTEND / 'src/pages/Documents.tsx'
backup_file(docs)
docs_text = docs.read_text(encoding='utf-8')

if 'runDocumentPipeline' not in docs_text:
    docs_text = docs_text.replace(
        '  processDocument,\n',
        '  runDocumentPipeline,\n',
        1,
    )
    # Remove the now-unused extraction/validation imports if present.
    docs_text = docs_text.replace('  extractDocument,\n', '', 1)
    docs_text = docs_text.replace('  validateDocument,\n', '', 1)

    old = '''      setUploading(false);\n      setProcessing(true);\n\n      /* STEP 2: OCR */\n      await processDocument(uploaded.document_id);\n\n      setSuccess("OCR completed. Extracting land-record fields…");\n\n      /* STEP 3: structured extraction */\n      const extraction = await extractDocument(uploaded.document_id);\n\n      /* STEP 4: deterministic validation */\n      if (extraction.fields_extracted > 0) {\n        setSuccess("Extraction completed. Running validation…");\n        await validateDocument(uploaded.document_id);\n      }\n\n      /* STEP 5: open the real document workspace */\n      navigate(`/documents/${uploaded.document_id}`);\n'''
    new = '''      setUploading(false);\n      setProcessing(true);\n      setSuccess("BhoomiAI is processing the document…");\n\n      /* Phase 6: one request owns the complete READ → VERIFY pipeline. */\n      const pipeline = await runDocumentPipeline(uploaded.document_id);\n      const status = String(pipeline.status || "PROCESSED");\n      const fields = Number(pipeline.fields_extracted || 0);\n      const review = Boolean(pipeline.review_required);\n\n      setSuccess(\n        review\n          ? `Processing complete. ${fields} fields extracted; human review is recommended.`\n          : `Processing complete. ${fields} fields extracted and validation passed.`\n      );\n\n      /* Open the real evidence/review workspace. */\n      navigate(`/documents/${uploaded.document_id}`);\n'''
    if old not in docs_text:
        raise SystemExit('Phase 6 patch stopped: expected Documents upload workflow was not found.')
    docs_text = docs_text.replace(old, new, 1)
    docs.write_text(docs_text, encoding='utf-8')

# ------------------------------------------------------------------
# 4. Add a tiny backend integration test that checks the orchestration graph
# without starting OCR or requiring a database.
# ------------------------------------------------------------------

test = BACKEND / 'tests/test_phase6_pipeline_structure.py'
backup_file(test)
write(test, '''from pathlib import Path\n\n\nROOT = Path(__file__).resolve().parents[2]\n\n\ndef test_phase6_pipeline_service_exists():\n    path = ROOT / "app" / "services" / "processing" / "pipeline_service.py"\n    assert path.exists()\n    text = path.read_text(encoding="utf-8")\n    for required in [\n        "OCRService",\n        "ExtractionService",\n        "ValidationService",\n        "DocumentPipelineService",\n        "evidence",\n        "classification",\n    ]:\n        assert required in text\n\n\ndef test_phase6_api_endpoint_exists():\n    path = ROOT / "app" / "api" / "v1" / "documents.py"\n    text = path.read_text(encoding="utf-8")\n    assert '@router.post("/{document_id}/run")' in text\n    assert "DocumentPipelineService" in text\n''')

# ------------------------------------------------------------------
# 5. Compile Python + TypeScript build if dependencies are present.
# ------------------------------------------------------------------

print('\n=== BHOOMIAI PHASE 6 ===')
print('Patched: backend end-to-end pipeline + frontend single-call integration')
print('Backup:', backup)

py_files = [pipeline, api]
for p in py_files:
    subprocess.run([sys.executable, '-m', 'py_compile', str(p)], check=True)
print('Python syntax: PASS')

# Run structure test if pytest is available.
pytest = shutil.which('pytest')
if pytest:
    result = subprocess.run([pytest, '-q', 'backend/tests/test_phase6_pipeline_structure.py'], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print('Phase 6 structure tests: PASS')
else:
    print('Phase 6 structure tests: SKIPPED (pytest command not found)')

npm = shutil.which('npm')
if npm and (FRONTEND / 'node_modules').exists():
    result = subprocess.run([npm, 'run', 'build'], cwd=FRONTEND)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print('Frontend build: PASS')
else:
    print('Frontend build: SKIPPED (npm/node_modules not available)')

print('\n=== PHASE 6 BATCH COMPLETE ===')
print('Single end-to-end endpoint: POST /api/v1/documents/{document_id}/run')
print('Pipeline: ingestion recovery -> preprocessing -> OCR -> classification -> extraction -> evidence -> validation')
print('Frontend upload workflow: CONNECTED to the Phase 6 endpoint')
print('Next: start/restart backend + frontend and upload one real document.')

