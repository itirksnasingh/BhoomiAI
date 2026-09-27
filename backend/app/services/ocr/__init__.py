from app.services.ocr.base import OCRBlockResult, OCRProvider, OCRResult
from app.services.ocr.document_classifier import DocumentClassification, LandDocumentClassifier
from app.services.ocr.ocr_service import OCRService
from app.services.ocr.tesseract import TesseractOCRProvider

__all__ = [
    "OCRBlockResult",
    "OCRProvider",
    "OCRResult",
    "DocumentClassification",
    "LandDocumentClassifier",
    "OCRService",
    "TesseractOCRProvider",
]