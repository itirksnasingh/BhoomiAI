from pathlib import Path
from uuid import uuid4


class LocalStorage:
    """
    Private local filesystem storage.

    Files are stored using generated UUID-based names rather than
    user-provided filenames.
    """

    def __init__(self, base_path: str | None = None):
        if base_path is None:
            # Resolve storage relative to the backend package,
            # not the process working directory.
            base_path = str(Path(__file__).resolve().parents[3] / "storage")
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_bytes(
        self,
        data: bytes,
        extension: str,
        folder: str = "uploads",
    ) -> str:
        """
        Save bytes using a generated filename.

        Returns a storage key rather than exposing the filesystem path.
        """

        extension = extension.lower()

        if extension and not extension.startswith("."):
            extension = f".{extension}"

        filename = f"{uuid4().hex}{extension}"

        directory = (self.base_path / folder).resolve()

        if self.base_path not in directory.parents and directory != self.base_path:
            raise ValueError("Invalid storage folder.")

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (directory / filename).resolve()

        if self.base_path not in file_path.parents:
            raise ValueError("Invalid storage path.")

        file_path.write_bytes(data)

        return str(
            Path(folder) / filename
        )

    def get_path(self, storage_key: str) -> Path:
        """
        Resolve a storage key to a private filesystem path.

        The resolved path must remain inside the configured storage root.
        """

        candidate = (self.base_path / storage_key).resolve()

        if self.base_path not in candidate.parents:
            raise ValueError(
                "Invalid storage key."
            )

        if not candidate.exists():
            raise FileNotFoundError(
                f"Stored file not found: {storage_key}"
            )

        return candidate
