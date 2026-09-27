from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


def _validate_file_signature(
    data: bytes,
    extension: str,
) -> None:
    """
    Validate the actual binary signature rather than trusting
    the filename or declared MIME type.
    """

    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError(
                "File content does not match PDF format."
            )

    elif extension in {".jpg", ".jpeg"}:
        if not data.startswith(b"\xff\xd8\xff"):
            raise ValueError(
                "File content does not match JPEG format."
            )

    elif extension == ".png":
        if not data.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            raise ValueError(
                "File content does not match PNG format."
            )

    elif extension in {".tif", ".tiff"}:
        if not (
            data.startswith(b"II*\x00")
            or data.startswith(b"MM\x00*")
        ):
            raise ValueError(
                "File content does not match TIFF format."
            )


async def validate_upload(
    file: UploadFile,
) -> bytes:
    """
    Validate an uploaded document before storage.

    Checks:
    - filename exists
    - extension is allowed
    - declared content type is allowed
    - file is not empty
    - configured size limit
    - binary signature matches extension
    """

    settings = get_settings()

    if not file.filename:
        raise ValueError("A filename is required.")

    if len(file.filename) > 255:
        raise ValueError(
            "Filename exceeds the maximum allowed length."
        )

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension: {extension}"
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Unsupported content type: {file.content_type}"
        )

    data = await file.read()

    if not data:
        raise ValueError("Uploaded file is empty.")

    max_file_size = (
        settings.max_upload_size_mb * 1024 * 1024
    )

    if len(data) > max_file_size:
        raise ValueError(
            "File exceeds the configured maximum upload size."
        )

    _validate_file_signature(
        data,
        extension,
    )

    return data
