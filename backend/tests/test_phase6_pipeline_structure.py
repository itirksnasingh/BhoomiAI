from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_phase6_pipeline_service_exists():
    path = ROOT / "app" / "services" / "processing" / "pipeline_service.py"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for required in [
        "OCRService",
        "ExtractionService",
        "ValidationService",
        "DocumentPipelineService",
        "evidence",
        "classification",
    ]:
        assert required in text


def test_phase6_api_endpoint_exists():
    path = ROOT / "app" / "api" / "v1" / "documents.py"
    text = path.read_text(encoding="utf-8")
    assert '@router.post("/{document_id}/run")' in text
    assert "DocumentPipelineService" in text
