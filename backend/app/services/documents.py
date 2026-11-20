"""Synthetic uploads only; no parsing, OCR, or citizen-document processing."""
import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.errors import APIError
from app.db.models import DocumentRecord
from app.db.repository import Repository, utc_now

# Extension, declared MIME and a minimal signature must all agree.
FILE_TYPES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}


class DocumentService:
    def __init__(self, repository: Repository, storage_dir: Path, max_bytes: int) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.max_bytes = max_bytes

    def store(self, upload: UploadFile) -> DocumentRecord:
        original = (upload.filename or "").replace("\\", "/").split("/")[-1]
        if not original or len(original) > 255 or any(ord(char) < 32 or ord(char) == 127 for char in original):
            raise APIError(400, "INVALID_FILENAME", "Provide a valid synthetic filename")
        extension = Path(original).suffix.lower()
        supported = FILE_TYPES.get(extension)
        if not supported or upload.content_type != supported[0]:
            raise APIError(415, "UNSUPPORTED_DOCUMENT_TYPE", "Supported synthetic files: PDF, PNG and JPEG")
        if upload.size is not None and upload.size > self.max_bytes:
            raise APIError(413, "FILE_TOO_LARGE", "File exceeds configured size limit")
        header = upload.file.read(16)
        if not header:
            raise APIError(400, "EMPTY_DOCUMENT", "Synthetic document must not be empty")
        if not header.startswith(supported[1]):
            raise APIError(415, "INVALID_DOCUMENT_SIGNATURE", "File signature does not match its declared type")
        upload.file.seek(0)
        identifier = str(uuid4())
        stored_filename = identifier + extension
        target = self.storage_dir / stored_filename
        size = 0
        digest = hashlib.sha256()
        created = False
        try:
            with target.open("xb") as destination:
                created = True
                while chunk := upload.file.read(64 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise APIError(413, "FILE_TOO_LARGE", "File exceeds configured size limit")
                    destination.write(chunk)
                    digest.update(chunk)
            record = DocumentRecord(identifier, original, stored_filename, supported[0], size,
                                    digest.hexdigest(), utc_now())
            self.repository.save_document(record)
            return record
        except Exception:
            if created:
                target.unlink(missing_ok=True)
            raise
