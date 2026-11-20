"""Optional local PostgreSQL adapter, using parameterized SQL and transactions."""
import json
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import uuid4

from app.db.models import AuditEvent, DocumentRecord, WorkflowRecord
from app.db.repository import StorageError, utc_now, validate_transition


class PostgresRepository:
    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError:
            raise StorageError("Install requirements-postgres.txt to use PostgreSQL") from None
        self._psycopg = psycopg
        self._dict_row = dict_row
        self._database_url = database_url

    @contextmanager
    def connection(self) -> Iterator[Any]:
        try:
            with self._psycopg.connect(self._database_url, row_factory=self._dict_row, connect_timeout=5,
                                      options="-c statement_timeout=5000") as conn:
                yield conn
        except self._psycopg.Error:
            raise StorageError("PostgreSQL operation failed") from None

    def initialize(self) -> None:
        statements = [
            """CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                state TEXT NOT NULL CHECK(state IN ('pending', 'running', 'completed', 'failed')),
                request_json JSONB NOT NULL, result_json JSONB, error_json JSONB,
                created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE, media_type TEXT NOT NULL,
                size_bytes BIGINT NOT NULL CHECK(size_bytes > 0), sha256 TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS document_audit_events (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
                event TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL)""",
            "CREATE INDEX IF NOT EXISTS ix_document_audit_document ON document_audit_events(document_id)",
        ]
        with self.connection() as conn:
            for statement in statements:
                conn.execute(statement)

    def create_workflow(self, request: dict) -> WorkflowRecord:
        identifier, now = str(uuid4()), utc_now()
        with self.connection() as conn:
            conn.execute("INSERT INTO workflows (id, state, request_json, created_at, updated_at) VALUES (%s, %s, %s::jsonb, %s, %s)",
                         (identifier, "pending", json.dumps(request), now, now))
        return WorkflowRecord(identifier, "pending", now, now)

    @staticmethod
    def _workflow(row: dict) -> WorkflowRecord:
        return WorkflowRecord(row["id"], row["state"], row["created_at"], row["updated_at"], row["result_json"], row["error_json"])

    def get_workflow(self, identifier: str) -> WorkflowRecord | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM workflows WHERE id = %s", (identifier,)).fetchone()
        return self._workflow(row) if row else None

    def transition_workflow(self, identifier: str, expected: str, state: str,
                            result: dict | None = None, error: dict | None = None) -> WorkflowRecord:
        validate_transition(expected, state)
        with self.connection() as conn:
            row = conn.execute(
                "UPDATE workflows SET state = %s, result_json = %s::jsonb, error_json = %s::jsonb, updated_at = %s WHERE id = %s AND state = %s RETURNING *",
                (state, json.dumps(result) if result is not None else None,
                 json.dumps(error) if error is not None else None, utc_now(), identifier, expected),
            ).fetchone()
            if row is None:
                raise ValueError("Workflow missing or state changed")
        return self._workflow(row)

    def save_document(self, record: DocumentRecord) -> None:
        with self.connection() as conn:
            conn.execute("INSERT INTO documents VALUES (%s, %s, %s, %s, %s, %s, %s)",
                         (record.id, record.original_filename, record.stored_filename, record.media_type,
                          record.size_bytes, record.sha256, record.created_at))
            conn.execute("INSERT INTO document_audit_events VALUES (%s, %s, %s, %s)",
                         (str(uuid4()), record.id, "synthetic_document.stored", record.created_at))

    def get_document(self, identifier: str) -> DocumentRecord | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = %s", (identifier,)).fetchone()
        return DocumentRecord(**row) if row else None

    def document_events(self, identifier: str) -> list[AuditEvent]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM document_audit_events WHERE document_id = %s ORDER BY created_at, id", (identifier,)).fetchall()
        return [AuditEvent(**row) for row in rows]
