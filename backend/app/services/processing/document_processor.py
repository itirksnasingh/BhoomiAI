from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentPage
from app.services.storage import LocalStorage


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


class DocumentProcessor:
    """Convert source files into clean, OCR-ready private page images."""

    def __init__(self, storage: LocalStorage | None = None):
        self.storage = storage or LocalStorage()

    def process_document(self, db: Session, document: Document, file_path: str) -> list[DocumentPage]:
        path = Path(file_path)
        extension = path.suffix.lower()
        if extension in IMAGE_EXTENSIONS:
            return self._process_image(db, document, path)
        if extension == ".pdf":
            return self._process_pdf(db, document, path)
        raise ValueError(f"Unsupported document format: {extension}")

    def _process_image(self, db: Session, document: Document, file_path: Path) -> list[DocumentPage]:
        with Image.open(file_path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            gray = ImageOps.grayscale(image)
            gray = ImageOps.autocontrast(gray, cutoff=1)
            buffer = BytesIO()
            gray.save(buffer, format="PNG", optimize=True)
            image_bytes = buffer.getvalue()

        storage_key = self.storage.save_bytes(
            data=image_bytes,
            extension=".png",
            folder=f"pages/{document.id}",
        )
        page = DocumentPage(
            document_id=document.id,
            page_number=1,
            image_storage_key=storage_key,
        )
        db.add(page)
        db.flush()
        return [page]

    def _process_pdf(self, db: Session, document: Document, file_path: Path) -> list[DocumentPage]:
        pdf = pymupdf.open(file_path)
        try:
            pages: list[DocumentPage] = []
            for page_number in range(1, len(pdf) + 1):
                pdf_page = pdf[page_number - 1]
                pixmap = pdf_page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                image_bytes = pixmap.tobytes("png")
                storage_key = self.storage.save_bytes(
                    data=image_bytes,
                    extension=".png",
                    folder=f"pages/{document.id}",
                )
                page = DocumentPage(
                    document_id=document.id,
                    page_number=page_number,
                    image_storage_key=storage_key,
                )
                db.add(page)
                pages.append(page)
            db.flush()
            return pages
        finally:
            pdf.close()


def process_document(db: Session, document: Document, file_path: str) -> list[DocumentPage]:
    return DocumentProcessor().process_document(db=db, document=document, file_path=file_path)
