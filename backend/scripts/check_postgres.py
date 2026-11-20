"""Integration check for a disposable PostgreSQL test database only."""
import os
import sys
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.db.postgres import PostgresRepository
from app.db.repository import StorageError
from app.main import create_app
from uuid import uuid4


def main() -> None:
    database_url = os.environ.get("DISHARI_TEST_DATABASE_URL")
    if not database_url:
        raise SystemExit("Set DISHARI_TEST_DATABASE_URL to a disposable PostgreSQL database first")
    with TemporaryDirectory(prefix="dishari-pg-check-") as temporary:
        settings = Settings(database_url=database_url, document_storage_dir=Path(temporary))
        with TestClient(create_app(settings)) as client:
            assert client.get("/health").status_code == 200
            response = client.post("/api/v1/workflows", json={"facts": {"quantity": 1, "confirmed": True}})
            assert response.status_code == 201
            workflow = response.json()
            assert workflow["state"] == "completed"
            assert client.get(f"/api/v1/workflows/{workflow['id']}").json() == workflow
            print("PASS PostgreSQL workflow creation, transitions and retrieval")
            response = client.post("/api/v1/documents", data={"synthetic": "true"},
                                   files={"file": ("synthetic.pdf", b"%PDF-1.4 Synthetic only", "application/pdf")})
            assert response.status_code == 201
            document_id = response.json()["id"]
            repository = client.app.state.repository
            assert isinstance(repository, PostgresRepository)
            document = repository.get_document(document_id)
            assert document is not None
            assert len(repository.document_events(document_id)) == 1
            print("PASS PostgreSQL document metadata and atomic audit event")
            try:
                repository.save_document(document)
                raise AssertionError("Duplicate document should fail")
            except StorageError:
                assert len(repository.document_events(document_id)) == 1
            invalid_id = str(uuid4())
            try:
                repository.save_document(replace(document, id=invalid_id, stored_filename=invalid_id + ".pdf", size_bytes=-1))
                raise AssertionError("Invalid size should fail")
            except StorageError:
                assert repository.get_document(invalid_id) is None
                assert repository.document_events(invalid_id) == []
            print("PASS PostgreSQL failure rollback and no partial audit writes")
            try:
                repository.transition_workflow(workflow["id"], "pending", "running")
                raise AssertionError("Stale state transition should fail")
            except ValueError:
                pass
            print("PASS PostgreSQL stale workflow state protection")
        with TestClient(create_app(settings)) as client:
            assert client.get(f"/api/v1/workflows/{workflow['id']}").json() == workflow
            assert client.app.state.repository.get_document(document_id) is not None
            print("PASS PostgreSQL records persist across application restart")
    print("5 PostgreSQL integration checks passed; only synthetic records were used")


if __name__ == "__main__":
    main()
