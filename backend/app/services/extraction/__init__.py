from app.services.extraction.field_extractor import FieldExtractor
from app.services.extraction.seven_twelve_table import SevenTwelveTableExtractor
from app.services.extraction.types import ExtractedFieldResult

__all__ = [
    "ExtractionService",
    "ExtractedFieldResult",
    "FieldExtractor",
    "SevenTwelveTableExtractor",
]


def __getattr__(name: str):
    if name == "ExtractionService":
        from app.services.extraction.extraction_service import ExtractionService
        return ExtractionService
    raise AttributeError(name)
