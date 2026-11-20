"""Persistence records. API schemas intentionally exclude internal storage paths."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WorkflowRecord:
    id: str
    state: str
    created_at: datetime
    updated_at: datetime
    result: dict | None = None
    error: dict | None = None


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    original_filename: str
    stored_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: datetime


@dataclass(frozen=True)
class AuditEvent:
    id: str
    document_id: str
    event: str
    created_at: datetime
