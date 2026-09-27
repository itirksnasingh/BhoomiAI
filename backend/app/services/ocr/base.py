from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRBlockResult:
    """
    Structured OCR result for one text block/line.
    """

    text: str
    confidence: float | None
    bbox: dict[str, int]
    language: str


@dataclass
class OCRResult:
    """
    Complete OCR result for one document page.
    """

    engine: str
    engine_version: str | None
    language: str
    text: str
    confidence: float | None
    blocks: list[OCRBlockResult]


class OCRProvider(ABC):
    """
    Interface implemented by every OCR engine used by BhoomiAI.
    """

    @abstractmethod
    def process(
        self,
        image_path: str,
        language: str = "mar+eng",
    ) -> OCRResult:
        """
        Run OCR on a single page image.
        """
        raise NotImplementedError