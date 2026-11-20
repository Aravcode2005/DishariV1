import hashlib
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.db.repository import StorageError
from app.main import create_app

PDF = b"%PDF-1.4\nSynthetic test only\n%%EOF"


def upload(client, filename="example.pdf", content=PDF, mime="application/pdf", declaration=True):
    return client.post("/api/v1/documents", files={"file": (filename, content, mime)},
                       data={"synthetic": "true"} if declaration else {})


@pytest.mark.parametrize("filename,content,mime", [
    ("example.pdf", PDF, "application/pdf"),
    ("example.png", b"\x89PNG\r\n\x1a\nSynthetic", "image/png"),
    ("example.jpeg", b"\xff\xd8\xffSynthetic", "image/jpeg"),
])
def test_synthetic_upload_and_audit(client, filename, content, mime):
    response = upload(client, filename, content, mime)
    assert response.status_code == 201
    body = response.json()
    assert body["synthetic"] is True
    assert body["size_bytes"] == len(content)
    assert body["sha256"] == hashlib.sha256(content).hexdigest()
    assert "stored_filename" not in body
    repository = client.app.state.repository
    record = repository.get_document(body["id"])
    assert record is not None
    target = client.app.state.document_service.storage_dir / record.stored_filename
    assert target.read_bytes() == content
    assert record.stored_filename.startswith(body["id"])
    assert repository.document_events(body["id"])[0].event == "synthetic_document.stored"


@pytest.mark.parametrize("filename,content,mime,status,code", [
    ("script.exe", b"MZ", "application/octet-stream", 415, "UNSUPPORTED_DOCUMENT_TYPE"),
    ("example.pdf", PDF, "image/png", 415, "UNSUPPORTED_DOCUMENT_TYPE"),
    ("example.pdf", b"fake PDF", "application/pdf", 415, "INVALID_DOCUMENT_SIGNATURE"),
    ("example.pdf", b"", "application/pdf", 400, "EMPTY_DOCUMENT"),
    ("example.pdf", b"%PDF-" + b"x" * 124, "application/pdf", 413, "FILE_TOO_LARGE"),
])
def test_invalid_documents(client, filename, content, mime, status, code):
    response = upload(client, filename, content, mime)
    assert response.status_code == status
    assert response.json()["code"] == code
    assert list(client.app.state.document_service.storage_dir.iterdir()) == []
    assert client.app.state.repository._documents == {}


def test_upload_requires_synthetic_declaration(client):
    assert upload(client, declaration=False).status_code == 422
    response = client.post("/api/v1/documents", files={"file": ("test.pdf", PDF, "application/pdf")}, data={"synthetic": "false"})
    assert response.status_code == 422
    assert list(client.app.state.document_service.storage_dir.iterdir()) == []


def test_safe_internal_filename(client):
    response = upload(client, "../../escape.pdf")
    assert response.status_code == 201
    record = client.app.state.repository.get_document(response.json()["id"])
    assert record.original_filename == "escape.pdf"
    assert "/" not in record.stored_filename and "\\" not in record.stored_filename


def test_temporary_storage_removed_on_shutdown(settings):
    with TestClient(create_app(settings)) as client:
        assert upload(client).status_code == 201
        directory = client.app.state.document_service.storage_dir
        assert directory.exists()
    assert not directory.exists()


def test_storage_failure_cleans_file(client, monkeypatch):
    def fail(record):
        raise StorageError("private-connection-details")

    monkeypatch.setattr(client.app.state.repository, "save_document", fail)
    response = upload(client)
    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_UNAVAILABLE"
    assert "private-connection-details" not in response.text
    assert list(client.app.state.document_service.storage_dir.iterdir()) == []


def test_streamed_file_size_checked_even_without_upload_size(client):
    service = client.app.state.document_service
    file = UploadFile(file=BytesIO(b"%PDF-" + b"x" * 200), filename="test.pdf",
                      headers={"content-type": "application/pdf"})
    try:
        with pytest.raises(Exception) as failure:
            service.store(file)
        assert failure.value.code == "FILE_TOO_LARGE"
        assert list(service.storage_dir.iterdir()) == []
    finally:
        file.file.close()


def test_whole_request_size_limit(client):
    response = client.post("/api/v1/documents", content=b"x" * 70000)
    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_TOO_LARGE"


def test_chunked_request_size_limit(client):
    def chunks():
        yield b"x" * 40000
        yield b"x" * 40000
    response = client.post("/api/v1/documents", content=chunks(),
                           headers={"Content-Type": "multipart/form-data; boundary=test"})
    assert response.status_code == 413
