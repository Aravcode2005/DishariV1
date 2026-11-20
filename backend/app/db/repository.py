"""Small storage interface and process-local MVP implementation."""
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.db.models import AuditEvent, DocumentRecord, WorkflowRecord


class StorageError(Exception):
    """Safe storage failure; never expose a connection string in API errors."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_transition(expected: str, state: str) -> None:
    if (expected, state) not in {("pending", "running"), ("running", "completed"), ("running", "failed")}:
        raise ValueError("Invalid workflow state transition")


class Repository(Protocol):
    def initialize(self) -> None: ...
    def create_workflow(self, request: dict) -> WorkflowRecord: ...
    def get_workflow(self, identifier: str) -> WorkflowRecord | None: ...
    def transition_workflow(self, identifier: str, expected: str, state: str,
                            result: dict | None = None, error: dict | None = None) -> WorkflowRecord: ...
    def save_document(self, record: DocumentRecord) -> None: ...
    def get_document(self, identifier: str) -> DocumentRecord | None: ...
    def document_events(self, identifier: str) -> list[AuditEvent]: ...


class MemoryRepository:
    """Not shared between processes; all records are lost on restart."""
    def __init__(self, max_records: int = 10_000) -> None:
        self._workflows: dict[str, WorkflowRecord] = {}
        self._documents: dict[str, DocumentRecord] = {}
        self._events: dict[str, list[AuditEvent]] = {}
        self._lock = RLock()
        self.max_records = max_records

    def initialize(self) -> None:
        pass

    def create_workflow(self, request: dict) -> WorkflowRecord:
        with self._lock:
            if len(self._workflows) >= self.max_records:
                raise StorageError("In-memory capacity reached")
            now = utc_now()
            record = WorkflowRecord(str(uuid4()), "pending", now, now)
            self._workflows[record.id] = record
            return deepcopy(record)

    def get_workflow(self, identifier: str) -> WorkflowRecord | None:
        with self._lock:
            return deepcopy(self._workflows.get(identifier))

    def transition_workflow(self, identifier: str, expected: str, state: str,
                            result: dict | None = None, error: dict | None = None) -> WorkflowRecord:
        validate_transition(expected, state)
        with self._lock:
            previous = self._workflows.get(identifier)
            if previous is None or previous.state != expected:
                raise ValueError("Workflow missing or state changed")
            record = WorkflowRecord(identifier, state, previous.created_at, utc_now(), deepcopy(result), deepcopy(error))
            self._workflows[identifier] = record
            return deepcopy(record)

    def save_document(self, record: DocumentRecord) -> None:
        with self._lock:
            if len(self._documents) >= self.max_records:
                raise StorageError("In-memory capacity reached")
            if record.id in self._documents:
                raise StorageError("Document already exists")
            self._documents[record.id] = record
            self._events[record.id] = [AuditEvent(str(uuid4()), record.id, "synthetic_document.stored", record.created_at)]

    def get_document(self, identifier: str) -> DocumentRecord | None:
        with self._lock:
            return self._documents.get(identifier)

    def document_events(self, identifier: str) -> list[AuditEvent]:
        with self._lock:
            return list(self._events.get(identifier, []))
