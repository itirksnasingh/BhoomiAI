from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentFile
from app.services.storage import LocalStorage


class DocumentStorageService:
    """
    Handles persistence of uploaded document files.

    The database stores metadata and a storage key.
    The actual file remains in private storage.
    """

    def __init__(self, storage: LocalStorage | None = None):
        self.storage = storage or LocalStorage()

    def store_document(
        self,
        db: Session,
        document: Document,
        data: bytes,
        original_filename: str,
        content_type: str,
    ) -> DocumentFile:
        """
        Store a document file and create its database metadata record.
        """

        extension = Path(original_filename).suffix

        storage_key = self.storage.save_bytes(
            data=data,
            extension=extension,
            folder=f"documents/{document.id}",
        )

        document_file = DocumentFile(
            document_id=document.id,
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=len(data),
        )

        db.add(document_file)
        db.flush()

        return document_file

    def get_document_file_path(
        self,
        document_file: DocumentFile,
    ) -> Path:
        """
        Resolve a stored document to its private filesystem path.
        """

        return self.storage.get_path(
            document_file.storage_key
        )